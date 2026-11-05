"""Browser acceptance against the real running BFF/Java/Python chain."""
from pathlib import Path
from playwright.sync_api import sync_playwright, expect


OUTPUT = Path("output/playwright")
OUTPUT.mkdir(parents=True, exist_ok=True)
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1050})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto("http://localhost:3000")
    page.wait_for_load_state("networkidle")
    page.get_by_role("button", name="载入虚构示例").click()
    page.get_by_role("button", name="分析匹配").click()
    expect(page.get_by_role("heading", name="匹配分析", exact=True)).to_be_visible(timeout=25000)
    expect(page.get_by_text("规则提取", exact=True)).to_be_visible()
    expect(page.get_by_text("Redis", exact=True)).to_be_visible()
    page.get_by_role("button", name="查看原文").first.click()
    expect(page.locator(".evidence-panel .highlight")).to_be_visible()
    page.get_by_role("tab", name="结构化简历").click()
    expect(page.get_by_role("heading", name="教育背景", exact=True)).to_be_visible()
    page.get_by_role("tab", name="岗位对照").click()
    page.get_by_label("岗位 JD", exact=True).fill("必须掌握 Java 和 Spring Boot，Docker 经验优先。")
    expect(page.get_by_text("材料已修改，以下是上一次分析结果。请重新分析。")).to_be_visible()
    with page.expect_download() as download:
        page.get_by_role("button", name="导出 JSON").click()
    assert download.value.suggested_filename == "careerlens-analysis.json"
    page.screenshot(path=str(OUTPUT / "desktop.png"), full_page=True)
    page.set_viewport_size({"width": 390, "height": 844})
    page.screenshot(path=str(OUTPUT / "mobile.png"), full_page=True)
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.set_viewport_size({"width": 1440, "height": 1050})
    page.route("**/api/v1/analyses", lambda route: route.fulfill(status=504, content_type="application/json", body='{"code":"UPSTREAM_TIMEOUT","msg":"分析超时，材料已保留。","data":null}'))
    page.get_by_role("button", name="分析匹配").click()
    expect(page.get_by_role("alert")).to_contain_text("分析超时")
    expect(page.get_by_label("简历文本", exact=True)).not_to_have_value("")
    page.unroute("**/api/v1/analyses")
    pending = []
    page.route("**/api/v1/analyses", lambda route: pending.append(route))
    page.get_by_role("button", name="分析匹配").click()
    expect(page.get_by_role("button", name="分析中", exact=True)).to_be_disabled()
    page.get_by_role("button", name="取消", exact=True).click()
    expect(page.get_by_role("button", name="分析匹配", exact=True)).to_be_enabled()
    for route in pending:
        route.abort()
    page.unroute_all(behavior="ignoreErrors")
    page.set_viewport_size({"width": 320, "height": 740})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert not errors, errors
    browser.close()
print("PASS browser: real analysis, evidence, structured resume, stale results, export, timeout recovery, cancel, 1440/390/320px")
