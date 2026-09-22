import { test, expect } from "@playwright/test";
import type { Session } from "../lib/types";
const seed: Session = {
  id: "edit-session",
  title: "测试连麦",
  topic: "职业",
  createdAt: 1,
  updatedAt: 2,
  draft: "尚未发送的草稿",
  messages: [
    {
      id: "u1",
      role: "user",
      content: "我做了五年运营",
      status: "complete",
      createdAt: 1,
    },
    {
      id: "a1",
      role: "assistant",
      content: "测试：第一轮回答",
      status: "complete",
      createdAt: 2,
    },
    {
      id: "u2",
      role: "user",
      content: "我负责用户增长",
      status: "complete",
      createdAt: 3,
    },
    {
      id: "a2",
      role: "assistant",
      content: "测试：旧的增长建议",
      status: "complete",
      createdAt: 4,
    },
    {
      id: "u3",
      role: "user",
      content: "后续旧问题",
      status: "complete",
      createdAt: 5,
    },
    {
      id: "a3",
      role: "assistant",
      content: "测试：后续旧回答",
      status: "complete",
      createdAt: 6,
    },
  ],
  summary: {
    decision: "旧问题",
    judgment: "旧判断",
    unknowns: "",
    actions: "用户编辑的小结",
    messageIds: ["u2"],
    basedOn: "a3",
    edited: true,
    evidence: [],
  },
};
test.beforeEach(async ({ page }) => {
  await page.route("**/api/status", (r) =>
    r.fulfill({ json: { configured: true } }),
  );
  await page.goto("/");
  await expect(page.locator("#message-input")).toBeEnabled();
  await page.evaluate(async (session) => {
    await new Promise<void>((resolve, reject) => {
      const r = indexedDB.open("paopao-room-v1", 1);
      r.onsuccess = () => {
        const tx = r.result.transaction("sessions", "readwrite");
        tx.objectStore("sessions").put(session);
        tx.oncomplete = () => {
          r.result.close();
          resolve();
        };
        tx.onerror = () => reject(tx.error);
      };
      r.onerror = () => reject(r.error);
    });
  }, seed);
  await page.reload();
  await expect(page.getByText("测试：后续旧回答")).toBeVisible();
});
test("editing earlier messages regenerates from the revised prefix, preserves draft and old summary, and survives refresh", async ({
  page,
}) => {
  let payload: { id: string; content: string }[] = [];
  await page.route("**/api/chat", (r) => {
    payload = r.request().postDataJSON().messages;
    return r.fulfill({
      contentType: "text/event-stream",
      body: 'data: {"type":"delta","text":"测试：基于修改后的新回答"}\n\ndata: {"type":"done"}\n\n',
    });
  });
  await page.evaluate(() => {
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: {
        writeText: async (text: string) => {
          document.documentElement.dataset.copiedText = text;
        },
      },
    });
  });
  await page.mouse.move(0, 0);
  const actions = page.locator("#message-u2 .message-actions");
  await expect(actions).toHaveCSS("opacity", "0");
  await page.locator("#message-u2").hover();
  await expect(actions).toHaveCSS("opacity", "1");
  await expect(actions.locator("time")).toHaveText(/\d{2}:\d{2}/);
  await actions.getByRole("button", { name: "复制", exact: true }).click();
  await expect(actions.getByRole("button", { name: "已复制" })).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute(
    "data-copied-text",
    "我负责用户增长",
  );
  await page.screenshot({
    path: "/tmp/paopao-message-actions.png",
    fullPage: true,
  });
  await page
    .locator("#message-u2")
    .getByRole("button", { name: "修改", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "保存并重新回答" }),
  ).toBeDisabled();
  await page.getByRole("textbox", { name: "修改消息", exact: true }).fill("");
  await expect(
    page.getByRole("button", { name: "保存并重新回答" }),
  ).toBeDisabled();
  await page
    .getByRole("textbox", { name: "修改消息", exact: true })
    .fill("更正：我负责客户咨询整理");
  await expect(page.locator("#message-input")).toBeDisabled();
  await page.getByRole("button", { name: "保存并重新回答" }).click();
  await expect(page.getByText("测试：基于修改后的新回答")).toBeVisible();
  expect(payload.map((m) => m.content)).toEqual([
    "我做了五年运营",
    "测试：第一轮回答",
    "更正：我负责客户咨询整理",
  ]);
  expect(payload[2].id).not.toBe("u2");
  await expect(page.getByText("测试：后续旧回答")).toBeHidden();
  await expect(page.locator("#message-input")).toHaveValue("尚未发送的草稿");
  await page.getByRole("button", { name: "本次小结" }).click();
  await expect(
    page.getByRole("button", { name: "整理这次连麦" }),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await page.reload();
  await expect(page.getByText("更正：我负责客户咨询整理")).toBeVisible();
  await expect(page.getByText("测试：基于修改后的新回答")).toBeVisible();
  await page.getByRole("button", { name: /^测试连麦（修改前）/ }).click();
  await expect(page.getByText("测试：后续旧回答")).toBeVisible();
  await page.getByRole("button", { name: "本次小结" }).click();
  await expect(page.getByLabel("下一步行动")).toHaveValue("用户编辑的小结");
});
test("mobile edit cancel makes no request; edited opening can fail and retry without losing the revision", async ({
  page,
}) => {
  let calls = 0;
  await page.route("**/api/chat", (r) => {
    calls++;
    return calls === 1
      ? r.fulfill({ status: 503, json: { error: "测试：连接失败" } })
      : r.fulfill({
          contentType: "text/event-stream",
          body: 'data: {"type":"delta","text":"测试：重试后的新回答"}\n\ndata: {"type":"done"}\n\n',
        });
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.locator("#message-u1 .message-actions")).toHaveCSS(
    "opacity",
    "1",
  );
  await page
    .locator("#message-u1")
    .getByRole("button", { name: "修改", exact: true })
    .click();
  await page
    .getByRole("textbox", { name: "修改消息", exact: true })
    .fill("取消的更改");
  await page.getByRole("button", { name: "取消", exact: true }).click();
  expect(calls).toBe(0);
  await expect(page.getByText("我做了五年运营", { exact: true })).toBeVisible();
  await page
    .locator("#message-u1")
    .getByRole("button", { name: "修改", exact: true })
    .click();
  await page
    .getByRole("textbox", { name: "修改消息", exact: true })
    .fill("我做了三年设计");
  await page.screenshot({
    path: "/tmp/paopao-message-edit-mobile.png",
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("button", { name: "保存并重新回答" }).click();
  await expect(page.getByText("回复未完成")).toBeVisible();
  await expect(
    page.getByRole("main").getByText("我做了三年设计", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "重新回复", exact: true }).click();
  await expect(page.getByText("测试：重试后的新回答")).toBeVisible();
  expect(calls).toBe(2);
  await expect(page.locator(".message.user")).toHaveCount(1);
  await page.reload();
  await expect(
    page.getByRole("main").getByText("我做了三年设计", { exact: true }),
  ).toBeVisible();
});

test("delete uses an in-page confirmation, supports cancel and Escape, and persists", async ({
  page,
}) => {
  // Reproduce hosts that suppress native JavaScript confirmation dialogs.
  await page.evaluate(() => {
    window.confirm = () => false;
  });
  const remove = page.getByRole("button", {
    name: "删除 测试连麦",
    exact: true,
  });
  const dialog = page.getByRole("dialog", { name: "删除这场连麦？" });
  await remove.click();
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("button", { name: "取消" })).toBeFocused();
  await dialog.getByRole("button", { name: "取消" }).click();
  await expect(remove).toBeVisible();
  await remove.click();
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  await expect(remove).toBeFocused();
  await remove.click();
  await dialog.getByRole("button", { name: "确认删除" }).click();
  await expect(remove).toHaveCount(0);
  await expect(page.getByText("测试：后续旧回答")).toHaveCount(0);
  await page.reload();
  await expect(remove).toHaveCount(0);
  await expect(page.locator("#message-input")).toHaveValue("");
});

test("deleting another session preserves the active draft; delete-all also persists", async ({
  page,
}) => {
  await page.getByRole("button", { name: "新开一场" }).click();
  await page.locator("#message-input").fill("保留这场草稿");
  await page
    .getByRole("button", { name: "删除 测试连麦", exact: true })
    .click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "确认删除" })
    .click();
  await expect(page.locator("#message-input")).toHaveValue("保留这场草稿");
  await page.reload();
  await expect(page.locator("#message-input")).toHaveValue("保留这场草稿");
  await page.getByRole("button", { name: "记录与隐私" }).click();
  await page
    .getByRole("button", { name: "删除全部本地记录", exact: true })
    .click();
  const dialog = page.getByRole("dialog", { name: "删除全部本地记录？" });
  await dialog.getByRole("button", { name: "取消" }).click();
  await expect(page.locator("#message-input")).toHaveValue("保留这场草稿");
  await page
    .getByRole("button", { name: "删除全部本地记录", exact: true })
    .click();
  await dialog.getByRole("button", { name: "确认删除" }).click();
  await expect(dialog).not.toBeVisible();
  await page.reload();
  await expect(page.locator(".history-row")).toHaveCount(0);
  await expect(page.locator("#message-input")).toHaveValue("");
});
