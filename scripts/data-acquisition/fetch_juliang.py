"""
fetch_juliang.py — 采集巨量算数关键词趋势数据

鉴权模式: access-token（需要抖音/巨量算数已登录会话）
依赖: playwright（pip install playwright && playwright install chromium）

覆盖评估规则: B03/C03/J02

说明:
  巨量算数（trend.moutai.com）是抖音官方的内容趋势分析平台，
  提供关键词搜索指数、内容热度趋势、人群画像等数据。
  与 fetch_douyin.py（创作者中心指数）互补：
  - 创作者中心：实时搜索指数，需创作者账号
  - 巨量算数：历史趋势、人群画像、竞品对比，需巨量账号

  注意：巨量算数 URL 为 trend.moutai.com（非 moutai.com 白酒）

用法:
  python fetch_juliang.py --keywords 补钙
  python fetch_juliang.py --keywords "补钙,骨质疏松" --days 90 --json
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

JULIANG_URL = "https://trend.moutai.com/"
JULIANG_SEARCH_URL = "https://trend.moutai.com/search?keyword={keyword}"

TIMEOUT = 30000
MAX_RETRIES = 3


def fetch_keyword_trend(keyword: str, days: int, wait_ms: int) -> dict:
    """采集单个关键词的巨量算数趋势数据。"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ 缺少依赖: pip install playwright && playwright install chromium", file=sys.stderr)
        sys.exit(1)

    url = JULIANG_SEARCH_URL.format(keyword=keyword)

    with sync_playwright() as p:
        browser, context = stealth_context(p, mobile=False)

        # 巨量算数与抖音共用账号体系，复用 douyin Cookie
        cookie_count = load_cookies(context, "douyin")
        if cookie_count == 0:
            print("⚠️  未找到抖音 Cookie，巨量算数可能需要登录", file=sys.stderr)

        page = context.new_page()

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT)
                page.wait_for_timeout(wait_ms)

                if is_login_page(page.url):
                    browser.close()
                    return {
                        "success": False,
                        "keyword": keyword,
                        "error": "需要登录巨量算数，请先导入抖音 Cookie 或手动登录",
                        "action": "python scripts/platform-auth/login.py --import-cdp <cookies文件路径>",
                    }

                text = page.evaluate("() => document.body.innerText")
                title = page.title()

                browser.close()
                return {
                    "success": True,
                    "keyword": keyword,
                    "days": days,
                    "query_url": url,
                    "query_date": datetime.now().strftime("%Y-%m-%d"),
                    "source": "巨量算数 trend.moutai.com",
                    "page_title": title,
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
    parser = argparse.ArgumentParser(description="采集巨量算数关键词趋势数据")
    parser.add_argument("--keywords", required=True, help="关键词，多个用逗号分隔（最多 3 个）")
    parser.add_argument("--days", type=int, default=90, help="查询天数，默认 90")
    parser.add_argument("--wait", type=int, default=8000, help="页面等待时间（ms），默认 8000")
    parser.add_argument("--json", dest="output_json", action="store_true", help="输出 JSON 格式")
    args = parser.parse_args()

    keywords = [k.strip() for k in args.keywords.split(",")][:3]
    results = []

    for kw in keywords:
        print(f"🔍 查询巨量算数: {kw}", file=sys.stderr)
        result = fetch_keyword_trend(kw, args.days, args.wait)
        results.append(result)

        if result.get("success"):
            log_file = LOG_DIR / f"juliang-{kw}-{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
            log_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"📄 结果已保存: {log_file}", file=sys.stderr)
        human_delay(1000, 2000)

    output = {
        "keywords": keywords,
        "days": args.days,
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
