"""
fetch_kaisi.py — 采集开思CHIS市场数据

鉴权模式: access-token（需要开思CHIS已登录会话，VIP账号）
依赖: playwright（pip install playwright && playwright install chromium）

覆盖评估规则: A02/A05/A06/D01-D04/H01-H11

注意: 开思CHIS 是 SPA 应用，直接访问子页面会 404。
      需通过主页搜索框触发搜索，再进入各数据模块。

用法:
  python fetch_kaisi.py --product 阿司匹林
  python fetch_kaisi.py --product 阿司匹林 --category 心脑血管 --wait 10000 --json
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

SESSION_DIR = Path(os.environ.get("SESSION_DIR", Path.home() / ".agent-browser" / "sessions"))
LOG_DIR = Path(".cms-log/log/product-eval-data-acquisition")
LOG_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://agent.sinohealth.com/chis"
TIMEOUT = 30000
MAX_RETRIES = 3
RETRY_INTERVAL = 3


def load_cookies(context, platform: str) -> int:
    """从文件加载 Cookie 到浏览器上下文。"""
    cookie_path = SESSION_DIR / f"{platform}-cookies.json"
    if not cookie_path.exists():
        return 0
    cookies = json.loads(cookie_path.read_text(encoding="utf-8"))
    if cookies:
        context.add_cookies(cookies)
    return len(cookies)


def fetch_kaisi_data(product: str, category: str | None, wait_ms: int) -> dict:
    """通过开思CHIS主页搜索产品，采集市场数据。"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ 缺少依赖: pip install playwright && playwright install chromium", file=sys.stderr)
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1440, "height": 900},
        )
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => false})")

        cookie_count = load_cookies(context, "kaisi")
        if cookie_count == 0:
            browser.close()
            return {
                "success": False,
                "error": "未找到开思CHIS Cookie，请先登录",
                "action": "python scripts/platform-auth/login.py --platform kaisi --manual",
            }

        page = context.new_page()

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                page.goto(BASE_URL, wait_until="domcontentloaded", timeout=TIMEOUT)
                page.wait_for_timeout(wait_ms)

                current_url = page.url
                if "login" in current_url.lower():
                    browser.close()
                    return {
                        "success": False,
                        "error": "Cookie 已过期，请重新登录",
                        "action": "python scripts/platform-auth/login.py --platform kaisi --manual",
                    }

                text = page.evaluate("() => document.body.innerText")
                title = page.title()

                # 尝试在搜索框中输入产品名
                search_selectors = [
                    'input[placeholder*="搜索"]',
                    'input[placeholder*="请输入"]',
                    'input[type="search"]',
                    '.search-input input',
                ]
                searched = False
                for sel in search_selectors:
                    try:
                        page.fill(sel, product)
                        page.keyboard.press("Enter")
                        page.wait_for_timeout(wait_ms)
                        text = page.evaluate("() => document.body.innerText")
                        searched = True
                        break
                    except Exception:
                        continue

                browser.close()
                return {
                    "success": True,
                    "product": product,
                    "category": category,
                    "query_date": datetime.now().strftime("%Y-%m-%d"),
                    "source": "开思CHIS agent.sinohealth.com",
                    "page_title": title,
                    "search_executed": searched,
                    "raw_text_preview": text[:3000],
                }

            except Exception as e:
                if attempt < MAX_RETRIES:
                    print(f"⚠️  第 {attempt} 次请求失败，{RETRY_INTERVAL}s 后重试: {e}", file=sys.stderr)
                    time.sleep(RETRY_INTERVAL)
                else:
                    browser.close()
                    return {"success": False, "error": str(e)}


def main() -> None:
    parser = argparse.ArgumentParser(description="采集开思CHIS市场数据")
    parser.add_argument("--product", required=True, help="产品名称或品类关键词")
    parser.add_argument("--category", help="品类筛选，如'心脑血管'")
    parser.add_argument("--wait", type=int, default=8000, help="页面等待时间（ms），默认 8000")
    parser.add_argument("--json", dest="output_json", action="store_true", help="输出 JSON 格式")
    args = parser.parse_args()

    print(f"🔍 查询开思CHIS: {args.product}", file=sys.stderr)

    result = fetch_kaisi_data(args.product, args.category, args.wait)

    if result.get("success"):
        log_file = LOG_DIR / f"kaisi-{args.product}-{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
        log_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"📄 结果已保存: {log_file}", file=sys.stderr)

    if args.output_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if result["success"]:
            print(f"\n✅ 开思CHIS查询成功")
            print(f"   产品: {result['product']}")
            print(f"   搜索已执行: {result['search_executed']}")
            print(f"   查询日期: {result['query_date']}")
            print(f"\n   页面内容预览（前 500 字）:")
            print(f"   {result['raw_text_preview'][:500]}")
        else:
            print(f"\n❌ 查询失败: {result['error']}")
            if result.get("action"):
                print(f"   建议操作: {result['action']}")


if __name__ == "__main__":
    main()
