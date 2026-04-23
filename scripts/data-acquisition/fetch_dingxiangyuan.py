"""
fetch_dingxiangyuan.py — 采集丁香园药品说明书与临床数据

鉴权模式: nologin（说明书公开）/ access-token（完整数据需登录）
依赖: playwright（pip install playwright && playwright install chromium）

覆盖评估规则: A00/A08/B01/B02/E01/E02/E03/G01/G02

说明:
  丁香园药品数据库（dxy.cn）提供说明书、适应症、用法用量、禁忌、
  不良反应等结构化数据，与药智网互补：
  - 药智网：批文/企业/医保/独家状态
  - 丁香园：说明书全文/临床用药指南/疾病诊疗路径

用法:
  python fetch_dingxiangyuan.py --product 门冬氨酸钙片
  python fetch_dingxiangyuan.py --product 阿司匹林 --type guideline --json
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _stealth import load_cookies, stealth_context, human_delay

LOG_DIR = Path(".cms-log/log/product-eval-data-acquisition")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 丁香园药品数据库搜索入口
DRUG_SEARCH_URL = "https://drugs.dxy.cn/pc/search?keyword={keyword}"
# 丁香园临床指南搜索
GUIDELINE_SEARCH_URL = "https://guide.dxy.cn/article/search?keyword={keyword}"

TIMEOUT = 30000
MAX_RETRIES = 3


def fetch_drug_info(product: str, query_type: str, wait_ms: int) -> dict:
    """采集丁香园药品说明书或临床指南数据。"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ 缺少依赖: pip install playwright && playwright install chromium", file=sys.stderr)
        sys.exit(1)

    url = (
        GUIDELINE_SEARCH_URL.format(keyword=product)
        if query_type == "guideline"
        else DRUG_SEARCH_URL.format(keyword=product)
    )

    with sync_playwright() as p:
        browser, context = stealth_context(p, mobile=False)
        # 丁香园部分内容无需登录，有 Cookie 可解锁更多
        load_cookies(context, "dingxiangyuan")
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
                    "product": product,
                    "query_type": query_type,
                    "query_url": url,
                    "query_date": datetime.now().strftime("%Y-%m-%d"),
                    "source": "丁香园 dxy.cn",
                    "page_title": title,
                    "raw_text_preview": text[:4000],
                }

            except Exception as e:
                if attempt < MAX_RETRIES:
                    print(f"⚠️  第 {attempt} 次请求失败，重试: {e}", file=sys.stderr)
                    time.sleep(2)
                else:
                    browser.close()
                    return {"success": False, "product": product, "error": str(e)}


def main() -> None:
    parser = argparse.ArgumentParser(description="采集丁香园药品说明书与临床数据")
    parser.add_argument("--product", required=True, help="产品名称或 API 名称")
    parser.add_argument(
        "--type",
        choices=["drug", "guideline"],
        default="drug",
        help="查询类型：drug（说明书）/ guideline（临床指南），默认 drug",
    )
    parser.add_argument("--wait", type=int, default=5000, help="页面等待时间（ms），默认 5000")
    parser.add_argument("--json", dest="output_json", action="store_true", help="输出 JSON 格式")
    args = parser.parse_args()

    print(f"🔍 查询丁香园 [{args.type}]: {args.product}", file=sys.stderr)

    result = fetch_drug_info(args.product, args.type, args.wait)

    if result.get("success"):
        log_file = LOG_DIR / f"dxy-{args.product}-{args.type}-{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
        log_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"📄 结果已保存: {log_file}", file=sys.stderr)

    if args.output_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if result["success"]:
            print(f"\n✅ 丁香园查询成功")
            print(f"   产品: {result['product']}")
            print(f"   类型: {result['query_type']}")
            print(f"   页面标题: {result['page_title']}")
            print(f"\n   内容预览（前 500 字）:")
            print(f"   {result['raw_text_preview'][:500]}")
        else:
            print(f"\n❌ 查询失败: {result['error']}")


if __name__ == "__main__":
    main()
