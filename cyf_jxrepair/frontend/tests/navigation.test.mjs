// 连接已启动的测试实例；仅登录和读取数据，不创建、重建或删除业务记录。
import assert from "node:assert/strict";
import { test } from "node:test";
import { chromium } from "playwright";

const base = process.env.E2E_BASE_URL || "http://127.0.0.1:8000";
const password = process.env.E2E_PASSWORD;

test("站内导航与页面生命周期", { skip: !password, timeout: 120_000 }, async (t) => {
  const browser = await chromium.launch({
    executablePath: process.env.E2E_CHROMIUM_PATH || undefined,
    args: ["--no-sandbox"],
  });
  t.after(() => browser.close());

  async function open(username) {
    const context = await browser.newContext();
    const page = await context.newPage();
    page.setDefaultTimeout(8000);
    const errors = [];
    page.on("pageerror", (err) => errors.push(err.message));
    await page.goto(`${base}/login.html`);
    await page.locator("#username").fill(username);
    await page.locator("#password").fill(password);
    await page.locator("#loginBtn").click();
    await page.waitForURL((url) => !url.pathname.endsWith("login.html"));
    await page.locator("header.topbar").waitFor();
    await page.locator("main[aria-busy]").waitFor({ state: "detached" });
    await page.evaluate(() => {
      window.navigationMarker = "same-document";
      window.originalTopbar = document.querySelector("header.topbar");
    });
    const documents = [];
    page.on("request", (request) => {
      if (request.resourceType() === "document") documents.push(request.url());
    });
    return { page, context, errors, documents };
  }

  async function go(page, href, ready) {
    await page.locator(`.nav a[href="${href}"]`).click();
    await page.waitForURL((url) => url.pathname.endsWith(`/${href}`));
    await page.locator("main[aria-busy]").waitFor({ state: "detached" });
    if (ready) await page.locator(ready).first().waitFor();
  }

  async function check(session, { close = true } = {}) {
    const { page, context, errors, documents } = session;
    assert.deepEqual(errors, []);
    assert.deepEqual(documents, [], "站内切换不应触发 document 请求");
    assert.equal(await page.locator("header.topbar").count(), 1);
    assert.equal(await page.evaluate(() => window.navigationMarker), "same-document");
    assert.equal(await page.evaluate(() => window.originalTopbar === document.querySelector("header.topbar")), true);
    if (close) await context.close();
  }

  await t.test("管理员全部导航、模板复用、图表释放和重新挂载", async () => {
    const session = await open("sbk01");
    const { page } = session;
    await page.locator("#chartMonthly svg").waitFor();
    await page.evaluate(() => {
      window.oldChart = echarts.getInstanceByDom(document.querySelector("#chartMonthly"));
    });
    let templates = 0;
    page.on("request", (request) => {
      if (new URL(request.url()).pathname === "/devices.html") templates++;
    });
    const routes = [
      ["devices.html", "#rows tr[data-id]", "设备台账"],
      ["orders.html", "#rows tr[data-id]", "全部工单"],
      ["knowledge.html", "#searchForm", "维修知识库"],
      ["users.html", "#rows tr[data-id]", "人员"],
      ["dispatch.html", "#tabs .tab", "派单"],
      ["dashboard.html", "#chartMonthly svg", "统计看板"],
      ["devices.html", "#rows tr[data-id]", "设备台账"],
    ];
    for (const [href, ready, title] of routes) {
      await go(page, href, ready);
      assert.equal(await page.title(), `${title} · CYF捷修云`);
      assert.equal(await page.locator(".nav a[aria-current=page]").getAttribute("href"), href);
    }
    assert.equal(templates, 1, "已加载的页面模板应复用");
    assert.equal(await page.evaluate(() => window.oldChart.isDisposed()), true);
    await page.locator("#addBtn").click();
    assert.equal(await page.getByRole("dialog").count(), 1);
    await page.getByRole("dialog").getByRole("button", { name: "取消", exact: true }).click();
    await check(session);
  });

  await t.test("筛选、详情返回、浏览器前进后退", async () => {
    const session = await open("sbk01");
    const { page } = session;
    await go(page, "orders.html", "#rows tr[data-id]");
    const filtered = page.waitForResponse((r) => r.url().includes("/api/orders?") && r.url().includes("status=ARCHIVED"));
    await page.locator('#tabs [data-status="ARCHIVED"]').click();
    await filtered;
    await page.locator("#rows tr[data-id]").first().waitFor();
    const url = page.url();
    const id = await page.locator("#rows tr[data-id]").first().getAttribute("data-id");
    await page.locator("#rows tr[data-id]").first().getByRole("link", { name: "详情", exact: true }).click();
    await page.waitForURL(`**/order-detail.html?id=${id}`);
    await page.locator("#docket .docket-title").waitFor();
    await page.locator("#backBtn").click();
    await page.waitForURL(url);
    await page.locator("#rows tr[data-id]").first().waitFor();
    assert.match(await page.locator("#tabs .active").innerText(), /已归档/);
    await page.goForward();
    await page.waitForURL(`**/order-detail.html?id=${id}`);
    await page.locator("#docket .docket-title").waitFor();
    await page.goBack();
    await page.waitForURL(url);
    await check(session);
  });

  await t.test("慢页面不能覆盖最后一次导航，包括返回当前菜单", async () => {
    const session = await open("sbk01");
    const { page } = session;
    let release;
    const gate = new Promise((resolve) => { release = resolve; });
    await page.route("**/devices.html", async (route) => {
      await gate;
      await route.continue().catch(() => {});
    });
    const requested = page.waitForRequest("**/devices.html");
    await page.locator('.nav a[href="devices.html"]').click();
    await requested;
    await page.locator('.nav a[href="dashboard.html"]').click();
    await page.locator("html.navigating").waitFor({ state: "detached" });
    release();
    await page.unrouteAll({ behavior: "wait" });
    assert.equal(new URL(page.url()).pathname, "/dashboard.html");
    await go(page, "devices.html", "#rows tr[data-id]");
    await check(session);
  });

  await t.test("加载失败保留当前页并允许重试", async () => {
    const session = await open("sbk01");
    const { page } = session;
    await page.route("**/devices.html", (route) => route.fulfill({ status: 503, body: "Unavailable" }));
    await page.locator('.nav a[href="devices.html"]').click();
    await page.locator(".toast-error").waitFor();
    assert.equal(new URL(page.url()).pathname, "/dashboard.html");
    await page.unroute("**/devices.html");
    await go(page, "devices.html", "#rows tr[data-id]");
    await check(session);
  });

  await t.test("离开页面后取消旧请求和搜索延迟任务", async () => {
    const session = await open("sbk01");
    const { page } = session;
    let release;
    const gate = new Promise((resolve) => { release = resolve; });
    await page.route("**/api/users?**", async (route) => {
      await gate;
      await route.continue().catch(() => {});
    });
    const requested = page.waitForRequest("**/api/users?**");
    await go(page, "users.html");
    const request = await requested;
    const cancelled = page.waitForEvent("requestfailed", (r) => r === request);
    await go(page, "devices.html", "#rows tr[data-id]");
    await cancelled;
    release();
    await page.unrouteAll({ behavior: "wait" });
    await page.locator("#keyword").fill("不应该延迟写入工单筛选");
    // 在输入处理器同一轮事件内导航，确保未到 debounce 的触发时间。
    await page.evaluate(async () => {
      const input = document.querySelector("#keyword");
      input.dispatchEvent(new Event("input", { bubbles: true }));
      document.querySelector('.nav a[href="orders.html"]').click();
    });
    await page.waitForURL("**/orders.html");
    await page.locator("#rows tr[data-id]").first().waitFor();
    assert.equal(await page.locator("#keyword").inputValue(), "");
    await check(session);
  });

  for (const [username, home, ready] of [
    ["dept01", "dashboard.html", "#chartMonthly svg"],
    ["emp01", "report.html", '#deviceId option[value="1"]'],
    ["wx01", "workbench.html", "#tabs .tab"],
  ]) {
    await t.test(`${username} 的导航、权限菜单与直接刷新`, async () => {
      const session = await open(username);
      const { page } = session;
      assert.equal(await page.locator('.nav a[href="devices.html"]').count(), 0);
      await go(page, "orders.html", "#tabs .tab");
      await go(page, "knowledge.html", "#searchForm");
      await page.locator('[data-q="异响"]').click();
      await page.waitForURL("**/knowledge.html?q=*");
      await page.locator("#results .skeleton").waitFor({ state: "detached" });
      assert.equal(await page.locator("#q").inputValue(), "异响");
      await go(page, home);
      await page.locator(ready).first().waitFor({ state: username === "emp01" ? "attached" : "visible" });
      if (username === "emp01") {
        await page.evaluate(async () => {
          const { navigate } = await import("/js/core/navigation.js");
          navigate("devices.html");
        });
        await page.locator(".toast-warning").waitFor();
        await page.waitForURL("**/report.html");
        await page.locator("main[aria-busy]").waitFor({ state: "detached" });
        assert.equal(await page.locator("#addBtn").count(), 0);
      }
      await check(session, { close: false });
      // 刷新是明确的整页行为：入口仍能独立打开，URL/角色和数据能恢复。
      await page.reload();
      await page.locator("header.topbar").waitFor();
      await page.locator(ready).first().waitFor({ state: username === "emp01" ? "attached" : "visible" });
      assert.equal(new URL(page.url()).pathname, `/${home}`);
      assert.deepEqual(session.errors, []);
      await session.context.close();
    });
  }
});
