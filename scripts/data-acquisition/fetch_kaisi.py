"""
fetch_kaisi.py — 采集开思数据市场数据

鉴权模式: access-token（需要开思数据已登录会话，VIP账号）
依赖: playwright（pip install playwright && playwright install chromium）

覆盖评估规则: A02/A05/A06/D01-D04/H01-H11

注意: 开思数据已升级为 AI 智能体界面（中康科技·天宫一号商用智能体），
      原搜索框路径已变更，当前通过页面文本采集原始内容供人工解读。

用法:
  python fetch_kaisi.py --product 阿司匹林
  python fetch_kaisi.py --product 阿司匹林 --category 心脑血管 --wait 12000 --json
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _stealth import load_cookies, stealth_context, human_delay, is_login_page

LOG_DIR = Path(".cms-log/log/product-eval-data-acquisition")
LOG_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://agent.sinohealth.com/chis"
TIMEOUT = 30000
MAX_RETRIES = 3
RETRY_INTERVAL = 3


def fetch_kaisi_data(product: str, category: str | None, wait_ms: int) -> dict:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ 缺少依赖: pip install playwright && playwright install chromium", file=sys.stderr)
        sys.exit(1)

    with sync_playwright() as p:
        browser, context = stealth_context(p, mobile=False)

        cookie_count = load_cookies(context, "kaisi")
        if cookie_count == 0:
            browser.close()
            return {
                "success": False,
                "error": "未找到开思数据 Cookie，请先导入或登录",
                "action": "python scripts/platform-auth/login.py --import-cdp <cookies文件路径>",
            }

        page = context.new_page()

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                page.goto(BASE_URL, wait_until="domcontentloaded", timeout=TIMEOUT)
                page.wait_for_timeout(wait_ms)

                if is_login_page(page.url):
                    browser.close()
                    return {
                        "success": False,
                        "error": "Cookie 已过期，请重新导入或登录",
                        "action": "python scripts/platform-auth/login.py --import-cdp <cookies文件路径>",
                    }

                text = page.evaluate("() => document.body.innerText")
                title = page.title()

                # 开思已升级为 AI 智能体界面，尝试多种搜索框选择器
                search_selectors = [
                    'input[placeholder*="搜索"]',
                    'input[placeholder*="请输入"]',
                    'input[placeholder*="输入"]',
                    'textarea[placeholder*="搜索"]',
                    'input[type="search"]',
                    'input[type="text"]',
                    '.search-input input',
                    '.ant-input',
                ]
                searched = False
                for sel in search_selectors:
                    try:
                        page.wait_for_selector(sel, timeout=2000)
                        page.fill(sel, product)
                        human_delay(300, 700)
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
                    "source": "开思数据 agent.sinohealth.com/chis",
                    "page_title": title,
                    "search_executed": searched,
                    "raw_text_preview": text[:4000],
                }

            except Exception as e:
                if attempt < MAX_RETRIES:
                    print(f"⚠️  第 {attempt} 次请求失败，{RETRY_INTERVAL}s 后重试: {e}", file=sys.stderr)
                    time.sleep(RETRY_INTERVAL)
                else:
                    browser.close()
                    return {"success": False, "error": str(e)}


def main() -> None:
    parser = argparse.ArgumentParser(description="采集开思数据市场数据")
    parser.add_argument("--product", required=True, help="产品名称或品类关键词")
    parser.add_argument("--category", help="品类筛选，如'心脑血管'")
    parser.add_argument("--wait", type=int, default=10000, help="页面等待时间（ms），默认 10000")
    parser.add_argument("--json", dest="output_json", action="store_true", help="输出 JSON 格式")
    args = parser.parse_args()

    print(f"🔍 查询开思数据: {args.product}", file=sys.stderr)

    result = fetch_kaisi_data(args.product, args.category, args.wait)

    if result.get("success"):
        log_file = LOG_DIR / f"kaisi-{args.product}-{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
        log_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"📄 结果已保存: {log_file}", file=sys.stderr)

    if args.output_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if result["success"]:
            print(f"\n✅ 开思数据查询成功")
            print(f"   产品: {result['product']}")
            print(f"   页面标题: {result['page_title']}")
            print(f"   搜索已执行: {result['search_executed']}")
            print(f"\n   页面内容预览（前 500 字）:")
            print(f"   {result['raw_text_preview'][:500]}")
        else:
            print(f"\n❌ 查询失败: {result['error']}")
            if result.get("action"):
                print(f"   建议操作: {result['action']}")


if __name__ == "__main__":
    main()
