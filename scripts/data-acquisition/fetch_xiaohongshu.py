"""
fetch_xiaohongshu.py — 采集小红书搜索结果数据

鉴权模式: access-token（推荐登录，未登录时部分数据受限）
依赖: playwright（pip install playwright && playwright install chromium）

覆盖评估规则: B03/C04/J02

用法:
  python fetch_xiaohongshu.py --keywords 阿司匹林
  python fetch_xiaohongshu.py --keywords "补钙,骨质疏松" --json
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _stealth import human_delay, is_login_page, load_cookies, stealth_context

LOG_DIR = Path(".cms-log/log/product-eval-data-acquisition")
LOG_DIR.mkdir(parents=True, exist_ok=True)

SEARCH_URL = "https://www.xiaohongshu.com/search_result?keyword={keyword}"
TIMEOUT = 30000
MAX_RETRIES = 3


def fetch_keyword(keyword: str, wait_ms: int) -> dict:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ 缺少依赖: pip install playwright && playwright install chromium", file=sys.stderr)
        sys.exit(1)

    with sync_playwright() as p:
        browser, context = stealth_context(p, mobile=False)
        cookie_count = load_cookies(context, "xiaohongshu")
        page = context.new_page()
        url = SEARCH_URL.format(keyword=keyword)

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT)
                page.wait_for_timeout(wait_ms)
                if is_login_page(page.url):
                    browser.close()
                    return {
                        "success": False,
                        "keyword": keyword,
                        "error": "Cookie 已过期，请重新登录或导入",
                        "action": "python scripts/platform-auth/login.py --platform xiaohongshu --manual",
                    }

                text = page.evaluate("() => document.body.innerText")
                title = page.title()
                browser.close()
                return {
                    "success": True,
                    "keyword": keyword,
                    "query_url": url,
                    "query_date": datetime.now().strftime("%Y-%m-%d"),
                    "source": "小红书 xiaohongshu.com",
                    "page_title": title,
                    "cookie_loaded": cookie_count > 0,
                    "raw_text_preview": text[:3000],
                }
            except Exception as e:
                if attempt < MAX_RETRIES:
                    print(f"⚠️  第 {attempt} 次请求失败，重试: {e}", file=sys.stderr)
                    time.sleep(2)
                else:
                    browser.close()
                    return {"success": False, "keyword": keyword, "error": str(e)}


def main() -> None:
    parser = argparse.ArgumentParser(description="采集小红书搜索结果数据")
    parser.add_argument("--keywords", required=True, help="关键词，多个用逗号分隔（最多 3 个）")
    parser.add_argument("--wait", type=int, default=8000, help="页面等待时间（ms），默认 8000")
    parser.add_argument("--json", dest="output_json", action="store_true", help="输出 JSON 格式")
    args = parser.parse_args()

    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()][:3]
    results = []

    for kw in keywords:
        print(f"🔍 查询小红书: {kw}", file=sys.stderr)
        result = fetch_keyword(kw, args.wait)
        results.append(result)
        if result.get("success"):
            log_file = LOG_DIR / f"xiaohongshu-{kw}-{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
            log_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"📄 结果已保存: {log_file}", file=sys.stderr)
        human_delay(1000, 2000)

    output = {
        "keywords": keywords,
        "query_date": datetime.now().strftime("%Y-%m-%d"),
        "results": results,
    }

    if args.output_json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        for r in results:
            if r["success"]:
                print(f"\n✅ 关键词: {r['keyword']}")
                print(f"   页面标题: {r.get('page_title', '')}")
                print(f"   内容预览: {r['raw_text_preview'][:300]}")
            else:
                print(f"\n❌ 关键词 {r['keyword']} 失败: {r['error']}")
                if r.get("action"):
                    print(f"   建议操作: {r['action']}")


if __name__ == "__main__":
    main()
