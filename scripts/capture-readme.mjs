// Isolated documentation preview: existing evaluation text, no personal history or model calls.
import { chromium } from '@playwright/test';
import { readFile, mkdir } from 'node:fs/promises';
const report = await readFile('paopao-perspective-skill/tests/voice-v2-results.md','utf8');
const answer = report.split('### Q1｜学 AI 工具但不敢做项目')[1].split('### Q2')[0].trim().split('\n').map(l=>l.replace(/^> ?/,'')).join('\n');
const browser = await chromium.launch({headless:true,...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH ? {executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH}: {})});
try {
  const page = await browser.newPage({viewport:{width:1600,height:1080},deviceScaleFactor:1,locale:'zh-CN',timezoneId:'Asia/Shanghai'});
  await page.route('**/api/status',r=>r.fulfill({json:{configured:true}}));
  await page.route('**/api/chat',r=>r.abort());
  await page.route('**/api/summary',r=>r.abort());
  // The README preview uses the user-provided local portrait.
  await page.route('**/paopao-avatar.png',r=>r.fulfill({path:process.env.PAOPAO_PREVIEW_AVATAR || 'public/paopao-avatar.png',contentType:'image/png'}));
  await page.goto('http://127.0.0.1:3000/');
  await page.locator('#message-input').waitFor();
  await page.evaluate(async answer=>{
    const time=Date.parse('2026-09-23T09:30:00+08:00');
    const session={id:'readme-demo',title:'从运营经验开始做 AI 项目',topic:'AI 转型',createdAt:time,updatedAt:time,draft:'',messages:[
      {id:'demo-question',role:'user',content:'做了五年运营，想转 AI 产品，但一直在学工具，还没做出项目。',createdAt:time,status:'complete'},
      {id:'demo-answer',role:'assistant',content:answer,createdAt:time+1000,status:'complete'}
    ],summary:{
      decision:'如何从五年运营经验出发，做出第一个 AI 产品项目。',
      judgment:'优先从熟悉的运营任务切入。先做出能运行的小项目，再根据实际问题补工具知识。',
      unknowns:'哪项重复任务最值得改进？目前耗时和错误率如何？谁能参与试用？',
      actions:'选一项重复任务，记录现状；做出最小版本，交给真实同事试用，再根据反馈调整。',
      messageIds:['demo-question','demo-answer'],evidence:[],basedOn:'demo-answer',edited:false
    }};
    await new Promise((resolve,reject)=>{
      const request=indexedDB.open('paopao-room-v1',1);
      request.onsuccess=()=>{const tx=request.result.transaction('sessions','readwrite');tx.objectStore('sessions').put(session);tx.oncomplete=()=>{request.result.close();resolve();};tx.onerror=()=>reject(tx.error);};request.onerror=()=>reject(request.error);
    });
  },answer);
  await page.reload();
  await page.getByText('从运营经验开始做 AI 项目',{exact:true}).waitFor();
  await page.getByRole('button',{name:'本次小结',exact:false}).click();
  await page.getByLabel('下一步行动').waitFor();
  await page.locator('#message-demo-question').scrollIntoViewIfNeeded();
  await page.locator('img').evaluateAll(images=>Promise.all(images.map(img=>img.decode().catch(()=>{}))));
  await page.mouse.move(20,20);
  await mkdir('docs/assets',{recursive:true});
  await page.screenshot({path:'docs/assets/chatroom.png',fullPage:true});
} finally {await browser.close();}
