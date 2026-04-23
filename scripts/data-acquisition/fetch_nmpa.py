"""
fetch_nmpa.py — 采集国家药监局批准文号与注册信息

鉴权模式: nologin（公开数据，无需登录）
依赖: playwright（pip install playwright && playwright install chromium）

覆盖评估规则: A00/A01/A04/A09/A10/F01/F02/H09

说明:
  国家药监局药品数据查询：https://www.nmpa.gov.cn/datasearch/home-index.html#category=yp
  查询内容：批准文号、企业名称、剂型、规格、适应症、批准日期、注册分类
  与药智网互补：NMPA 为官方权威来源，药智网提供更丰富的历史数据和市场信息

用法:
  python fetch_nmpa.py --product 门冬氨酸钙片
  python fetch_nmpa.py --approval-number H20041573 --json
  python fetch_nmpa.py --product 阿司匹林 --type anda --json
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _stealth import stealth_context, human_delay

LOG_DIR = Path(".cms-log/log/product-eval-data-acquisition")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# NMPA 药品数据查询入口
NMPA_DRUG_URL = "https://www.nmpa.gov.cn/datasearch/home-index.html#category=yp"
# NMPA 药品注册批件查询（直接搜索接口）
NMPA_SEARCH_URL = "https://www.nmpa.gov.cn/datasearch/search-info.html#category=yp&keyword={keyword}"

TIMEOUT = 30000
MAX_RETRIES = 3


def fetch_nmpa_data(keyword: str, wait_ms: int) -> dict:
    """采集 NMPA 药品注册信息。"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ 缺少依赖: pip install playwright && playwright install chromium", file=sys.stderr)
        sys.exit(1)

    url = NMPA_SEARCH_URL.format(keyword=keyword)

    with sync_playwright() as p:
        # NMPA 无需登录，用 Desktop UA
        browser, context = stealth_context(p, mobile=False)
        page = context.new_page()

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT)
                page.wait_for_timeout(wait_ms)

                text = page.evaluate("() => document.body.innerText")
                title = page.title()

                browser.close()
                return {
                    "success": True,
                    "keyword": keyword,
                    "query_url": url,
                    "query_date": datetime.now().strftime("%Y-%m-%d"),
                    "source": "国家药监局 nmpa.gov.cn",
                    "page_title": title,
                    "raw_text_preview": text[:4000],
                }

            except Exception as e:
                if attempt < MAX_RETRIES:
                    print(f"⚠️  第 {attempt} 次请求失败，重试: {e}", file=sys.stderr)
                    time.sleep(2)
                else:
                    browser.close()
                    return {"success": False, "keyword": keyword, "error": str(e)}


def main() -> None:
    parser = argparse.ArgumentParser(description="采集国家药监局批准文号与注册信息")
    parser.add_argument("--product", help="产品名称或 API 名称")
    parser.add_argument("--approval-number", help="批准文号（如 H20041573）")
    parser.add_argument("--wait", type=int, default=6000, help="页面等待时间（ms），默认 6000")
    parser.add_argument("--json", dest="output_json", action="store_true", help="输出 JSON 格式")
    args = parser.parse_args()

    keyword = args.approval_number or args.product
    if not keyword:
        parser.error("请提供 --product 或 --approval-number")

    print(f"🔍 查询 NMPA: {keyword}", file=sys.stderr)

    result = fetch_nmpa_data(keyword, args.wait)

    if result.get("success"):
        log_file = LOG_DIR / f"nmpa-{keyword}-{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
        log_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"📄 结果已保存: {log_file}", file=sys.stderr)

    if args.output_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if result["success"]:
            print(f"\n✅ NMPA 查询成功")
            print(f"   关键词: {result['keyword']}")
            print(f"   查询日期: {result['query_date']}")
            print(f"\n   内容预览（前 500 字）:")
            print(f"   {result['raw_text_preview'][:500]}")
        else:
            print(f"\n❌ 查询失败: {result['error']}")


if __name__ == "__main__":
    main()
