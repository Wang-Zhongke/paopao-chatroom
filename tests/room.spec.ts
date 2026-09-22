import { test, expect } from "@playwright/test";
test("unconfigured desktop and mobile: editable examples, draft persistence, no fake sending", async ({
  page,
}) => {
  await page.route("**/api/status", (r) =>
    r.fulfill({ json: { configured: false } }),
  );
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: /你最近，\s*在纠结什么？/ }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "开始聊" })).toBeDisabled();
  await page.getByRole("button", { name: "想转 AI", exact: false }).click();
  await expect(page.locator("#message-input")).toHaveValue(/五年运营/);
  await page.reload();
  await expect(page.locator("#message-input")).toHaveValue(/五年运营/);
  await page.screenshot({ path: "/tmp/paopao-desktop.png", fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: "/tmp/paopao-mobile.png", fullPage: true });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("button", { name: "打开会话菜单" }).click();
  await expect(page.getByRole("button", { name: "记录与隐私" })).toBeVisible();
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "查看说明" }).click();
  await expect(
    page.getByRole("heading", { name: "尚未配置回复服务" }),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(
    page.getByRole("heading", { name: "尚未配置回复服务" }),
  ).toBeHidden();
});
test("mock transport: stream failure, retry, correction, summary editing, restore and delete", async ({
  page,
}) => {
  await page.route("**/api/status", (r) =>
    r.fulfill({ json: { configured: true } }),
  );
  let count = 0;
  let requestMessages: unknown[] = [];
  await page.route("**/api/chat", async (r) => {
    count++;
    requestMessages = r.request().postDataJSON().messages;
    const events =
      count === 1
        ? [
            { type: "delta", text: "测试：部分回复" },
            { type: "error", error: "测试：连接中断" },
          ]
        : [
            {
              type: "delta",
              text:
                count === 2
                  ? "测试：你已有的运营经验可以保留。"
                  : "测试：收到纠正，判断需要调整。",
            },
            { type: "done" },
          ];
    await r.fulfill({
      contentType: "text/event-stream",
      body: events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join(""),
    });
  });
  await page.route("**/api/summary", (r) => {
    const ms = r.request().postDataJSON().messages;
    return r.fulfill({
      json: {
        decision: "测试：是否转型",
        judgment: "测试：先验证业务问题",
        unknowns: "待确认项目",
        actions: "找业务同事聊聊",
        messageIds: [ms[0].id],
        evidence: [],
      },
    });
  });
  await page.goto("/");
  await page.locator("#message-input").fill("做了五年运营，想转 AI");
  await page.getByRole("button", { name: "开始聊" }).click();
  await expect(page.getByText("测试：部分回复")).toBeVisible();
  await expect(page.getByText("回复未完成")).toBeVisible();
  await page.getByRole("button", { name: "重新回复" }).click();
  await expect(
    page.getByText("测试：你已有的运营经验可以保留。"),
  ).toBeVisible();
  expect(requestMessages).toHaveLength(1);
  await page.locator("#message-input").fill("纠正一下，是三年运营");
  await page.getByRole("button", { name: /^发送/ }).click();
  await expect(page.getByText("测试：收到纠正，判断需要调整。")).toBeVisible();
  expect(requestMessages).toHaveLength(3);
  await page.getByRole("button", { name: "本次小结" }).click();
  await page.getByRole("button", { name: "整理这次连麦" }).click();
  await expect(page.getByLabel("你正在决定的事")).toHaveValue("测试：是否转型");
  await page.getByLabel("下一步行动").fill("我自己改的行动");
  await page.reload();
  await page.getByRole("button", { name: "本次小结" }).click();
  await expect(page.getByLabel("下一步行动")).toHaveValue("我自己改的行动");
  await page.screenshot({
    path: "/tmp/paopao-conversation.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "更新连麦小结" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "取消" }).click();
  await expect(page.getByLabel("下一步行动")).toHaveValue("我自己改的行动");
  await page.getByRole("button", { name: "更新连麦小结" }).click();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await expect(page.getByLabel("下一步行动")).toHaveValue("我自己改的行动");
  await page.getByRole("button", { name: "更新连麦小结" }).click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "确认更新" })
    .click();
  await expect(page.getByLabel("下一步行动")).toHaveValue("找业务同事聊聊");
  await page.reload();
  await page.getByRole("button", { name: "本次小结" }).click();
  await expect(page.getByLabel("下一步行动")).toHaveValue("找业务同事聊聊");
  await page
    .locator(".drawer")
    .getByRole("button", { name: "关闭侧栏" })
    .click();
  await page.locator("#message-input").fill("再补充一个事实");
  await page.getByRole("button", { name: /^发送/ }).click();
  await expect(page.locator(".message.assistant")).toHaveCount(3);
  await page.getByRole("button", { name: "本次小结" }).click();
  await expect(page.getByText("小结有新内容可更新")).toBeVisible();
  await page
    .locator(".drawer")
    .getByRole("button", { name: "关闭侧栏" })
    .click();
  await page.getByRole("button", { name: /删除 做了五年/ }).click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "确认删除" })
    .click();
  await expect(
    page.getByRole("heading", { name: /你最近，\s*在纠结什么？/ }),
  ).toBeVisible();
});
test("mock transport: stop leaves unfinished response and composer reusable", async ({
  page,
}) => {
  await page.route("**/api/status", (r) =>
    r.fulfill({ json: { configured: true } }),
  );
  await page.route("**/api/chat", async (r) => {
    await new Promise((resolve) => setTimeout(resolve, 1500));
    await r
      .fulfill({
        contentType: "text/event-stream",
        body: 'data: {"type":"done"}\n\n',
      })
      .catch(() => {});
  });
  await page.goto("/");
  await page.locator("#message-input").fill("想换工作");
  await page.getByRole("button", { name: "开始聊" }).click();
  await page.getByRole("button", { name: "停止回复" }).click();
  await expect(page.getByText("回复已停止")).toBeVisible();
  await page.locator("#message-input").fill("补充情况");
  await expect(page.getByRole("button", { name: /^发送/ })).toBeEnabled();
});
test("real routes accept browser same-origin and reject cross-origin without model calls", async ({
  page,
  request,
}) => {
  await page.goto("/");
  for (const endpoint of ["/api/chat", "/api/summary"]) {
    // Empty messages test validation after the origin gate, without model calls.
    const response = await page.evaluate(async (endpoint) => {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: [] }),
      });
      return { status: res.status, body: await res.json() };
    }, endpoint);
    expect(response.status).toBe(400);
    expect(response.body.error).toBe("请求内容无效，请检查后重试。");
    const rejected = await request.post(endpoint, {
      headers: { Origin: "https://untrusted.example" },
      data: { messages: [] },
    });
    expect(rejected.status()).toBe(400);
    expect((await rejected.json()).error).toBe("请求来源不允许。");
  }
});
