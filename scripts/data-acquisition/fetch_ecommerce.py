"""
fetch_ecommerce.py — 采集京东/天猫/美团/京东到家/饿了么电商平台数据

鉴权模式: access-token（推荐登录，未登录时部分数据受限）
依赖: playwright（pip install playwright && playwright install chromium）

覆盖评估规则: A02/A03/A06/A07/C04/I03/I04

平台分组:
  --platform b2c   → 京东 + 天猫（B2C 运营能力）
  --platform o2o   → 美团 + 京东到家 + 饿了么（O2O 运营能力）
  --platform all   → 全部五个平台（默认）

用法:
  python fetch_ecommerce.py --product 阿司匹林
  python fetch_ecommerce.py --product 阿司匹林 --platform b2c --pages 5 --json
  python fetch_ecommerce.py --product 阿司匹林 --platform o2o --json
"""

import argparse
import json
import random
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _stealth import load_cookies, stealth_context, human_delay

LOG_DIR = Path(".cms-log/log/product-eval-data-acquisition")
LOG_DIR.mkdir(parents=True, exist_ok=True)

PLATFORM_CONFIGS = {
    "jd": {
        "name": "京东",
        "search_url": "https://search.jd.com/Search?keyword={keyword}&enc=utf-8",
        "cookie_key": "jd",
        "mobile": False,
    },
    "tmall": {
        "name": "天猫",
        "search_url": "https://list.tmall.com/search_product.htm?q={keyword}",
        "cookie_key": "tmall",
        "mobile": False,
    },
    "meituan": {
        "name": "美团",
        "search_url": "https://www.meituan.com/search/?q={keyword}",
        "cookie_key": "meituan",
        "mobile": False,
    },
    "jddaojia": {
        "name": "京东到家",
        "search_url": "https://daojia.jd.com/search?keyword={keyword}",
        "cookie_key": "jd",   # 京东到家与京东共用 Cookie
        "mobile": False,
    },
    "eleme": {
        "name": "饿了么",
        "search_url": "https://h5.ele.me/search/?keyword={keyword}",
        "cookie_key": "eleme",
        "mobile": True,
    },
}

TIMEOUT = 30000
MAX_RETRIES = 3
RETRY_INTERVAL = 3


def fetch_platform(product: str, platform_key: str, pages: int, wait_ms: int = 4000) -> dict:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ 缺少依赖: pip install playwright && playwright install chromium", file=sys.stderr)
        sys.exit(1)

    config = PLATFORM_CONFIGS[platform_key]
    url = config["search_url"].format(keyword=product)

    with sync_playwright() as p:
        browser, context = stealth_context(p, mobile=config["mobile"])
        load_cookies(context, config["cookie_key"])
        page = context.new_page()

        all_text = []
        for page_num in range(1, pages + 1):
            page_url = url if page_num == 1 else f"{url}&page={page_num}"
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    page.goto(page_url, wait_until="domcontentloaded", timeout=TIMEOUT)
                    page.wait_for_timeout(wait_ms + random.randint(0, 2000))
                    text = page.evaluate("() => document.body.innerText")
                    all_text.append(text)
                    human_delay(500, 1500)
                    break
                except Exception as e:
                    if attempt < MAX_RETRIES:
                        time.sleep(RETRY_INTERVAL)
                    else:
                        print(f"⚠️  第 {page_num} 页采集失败: {e}", file=sys.stderr)

        browser.close()

    combined_text = "\n".join(all_text)
    return {
        "platform": platform_key,
        "platform_name": config["name"],
        "product": product,
        "pages_fetched": len(all_text),
        "query_url": url,
        "query_date": datetime.now().strftime("%Y-%m-%d"),
        "raw_text_preview": combined_text[:4000],
        "text_length": len(combined_text),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="采集京东/天猫/美团/京东到家/饿了么电商平台数据")
    parser.add_argument("--product", required=True, help="搜索关键词")
    parser.add_argument(
        "--platform",
        choices=["jd", "tmall", "meituan", "jddaojia", "eleme", "all", "o2o", "b2c"],
        default="all",
        help="采集平台：jd/tmall/meituan/jddaojia/eleme/all/o2o/b2c，默认 all",
    )
    parser.add_argument("--pages", type=int, default=3, help="采集页数，默认 3")
    parser.add_argument("--wait", type=int, default=4000, help="每页等待时间（ms），默认 4000")
    parser.add_argument("--json", dest="output_json", action="store_true", help="输出 JSON 格式")
    args = parser.parse_args()

    platform_map = {
        "all": ["jd", "tmall", "meituan", "jddaojia", "eleme"],
        "o2o": ["meituan", "jddaojia", "eleme"],
        "b2c": ["jd", "tmall"],
    }
    platforms = platform_map.get(args.platform, [args.platform])
    results = []

    for plat in platforms:
        print(f"🔍 采集 {PLATFORM_CONFIGS[plat]['name']}: {args.product}", file=sys.stderr)
        result = fetch_platform(args.product, plat, args.pages, args.wait)
        results.append(result)

        log_file = LOG_DIR / f"{plat}-{args.product}-{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
        log_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"📄 结果已保存: {log_file}", file=sys.stderr)

    output = {"product": args.product, "query_date": datetime.now().strftime("%Y-%m-%d"), "platforms": results}

    if args.output_json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        for r in results:
            print(f"\n✅ {r['platform_name']} 采集完成")
            print(f"   采集页数: {r['pages_fetched']}")
            print(f"   内容长度: {r['text_length']} 字符")
            print(f"   预览: {r['raw_text_preview'][:300]}")


if __name__ == "__main__":
    main()
