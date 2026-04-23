"""
fetch_douyin.py — 采集抖音关键词指数

鉴权模式: access-token（需要抖音创作服务平台已登录会话）
依赖: playwright（pip install playwright && playwright install chromium）

覆盖评估规则: B03/C03/J02

注意: 巨量算数已于2026年1月升级为"抖音指数"，集成在抖音创作者中心。
      无需单独账号，用抖音账号登录 creator.douyin.com 即可。

用法:
  python fetch_douyin.py --keywords 阿司匹林
  python fetch_douyin.py --keywords "阿司匹林,心脑血管,血栓" --days 30 --json
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

INDEX_URL = "https://creator.douyin.com/creator-micro/creator-count/arithmetic-index"
TIMEOUT = 30000
MAX_RETRIES = 3
RETRY_INTERVAL = 2
THRESHOLD_C03 = 50000  # C03 规则阈值：搜索指数均值 ≥ 5 万


def load_cookies(context, platform: str) -> int:
    """从文件加载 Cookie 到浏览器上下文。"""
    cookie_path = SESSION_DIR / f"{platform}-cookies.json"
    if not cookie_path.exists():
        return 0
    cookies = json.loads(cookie_path.read_text(encoding="utf-8"))
    if cookies:
        context.add_cookies(cookies)
    return len(cookies)


def fetch_keyword_index(keyword: str, days: int, wait_ms: int = 5000) -> dict:
    """采集单个关键词的抖音指数。"""
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

        cookie_count = load_cookies(context, "douyin")
        if cookie_count == 0:
            browser.close()
            return {
                "success": False,
                "keyword": keyword,
                "error": "未找到抖音 Cookie，请先登录",
                "action": "python scripts/platform-auth/login.py --platform douyin --username <手机号>",
            }

        page = context.new_page()

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                page.goto(INDEX_URL, wait_until="domcontentloaded", timeout=TIMEOUT)
                page.wait_for_timeout(wait_ms)

                current_url = page.url
                if "login" in current_url.lower() or "passport" in current_url.lower():
                    browser.close()
                    return {
                        "success": False,
                        "keyword": keyword,
                        "error": "Cookie 已过期，请重新登录",
                        "action": "python scripts/platform-auth/login.py --platform douyin --username <手机号>",
                    }

                # 尝试在搜索框输入关键词
                search_selectors = [
                    'input[placeholder*="关键词"]',
                    'input[placeholder*="搜索"]',
                    '.search-input input',
                ]
                searched = False
                for sel in search_selectors:
                    try:
                        page.fill(sel, keyword)
                        page.keyboard.press("Enter")
                        page.wait_for_timeout(wait_ms)
                        searched = True
                        break
                    except Exception:
                        continue

                text = page.evaluate("() => document.body.innerText")
                browser.close()

                return {
                    "success": True,
                    "keyword": keyword,
                    "days": days,
                    "query_date": datetime.now().strftime("%Y-%m-%d"),
                    "source": "抖音创作服务平台 creator.douyin.com",
                    "search_executed": searched,
                    "raw_text_preview": text[:2000],
                }

            except Exception as e:
                if attempt < MAX_RETRIES:
                    print(f"⚠️  第 {attempt} 次请求失败，{RETRY_INTERVAL}s 后重试: {e}", file=sys.stderr)
                    time.sleep(RETRY_INTERVAL)
                else:
                    browser.close()
                    return {"success": False, "keyword": keyword, "error": str(e)}


def main() -> None:
    parser = argparse.ArgumentParser(description="采集抖音关键词指数")
    parser.add_argument("--keywords", required=True, help="关键词，多个用逗号分隔（最多 3 个）")
    parser.add_argument("--days", type=int, default=30, help="查询天数，默认 30")
    parser.add_argument("--wait", type=int, default=5000, help="页面等待时间（ms），默认 5000")
    parser.add_argument("--json", dest="output_json", action="store_true", help="输出 JSON 格式")
    args = parser.parse_args()

    keywords = [k.strip() for k in args.keywords.split(",")][:3]
    results = []

    for kw in keywords:
        print(f"🔍 查询抖音指数: {kw}", file=sys.stderr)
        result = fetch_keyword_index(kw, args.days, args.wait)
        results.append(result)

        if result.get("success"):
            log_file = LOG_DIR / f"douyin-{kw}-{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
            log_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"📄 结果已保存: {log_file}", file=sys.stderr)

    output = {
        "keywords": keywords,
        "days": args.days,
        "query_date": datetime.now().strftime("%Y-%m-%d"),
        "threshold_c03": THRESHOLD_C03,
        "results": results,
    }

    if args.output_json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        for r in results:
            if r["success"]:
                print(f"\n✅ 关键词: {r['keyword']}")
                print(f"   搜索已执行: {r['search_executed']}")
                print(f"   内容预览: {r['raw_text_preview'][:300]}")
            else:
                print(f"\n❌ 关键词 {r['keyword']} 失败: {r['error']}")
                if r.get("action"):
                    print(f"   建议操作: {r['action']}")


if __name__ == "__main__":
    main()
