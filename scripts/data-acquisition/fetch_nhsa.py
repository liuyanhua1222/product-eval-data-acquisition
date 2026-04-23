"""
fetch_nhsa.py — 采集国家医保局药品目录与医保类别

鉴权模式: nologin（公开数据，无需登录）
依赖: playwright（pip install playwright && playwright install chromium）

覆盖评估规则: A00（医保类别字段）

说明:
  国家医保局药品目录查询：https://www.nhsa.gov.cn/
  查询内容：医保甲/乙类、医保编码、适应症限制、报销比例
  用于补充 A00 产品基础信息中的医保身份字段

用法:
  python fetch_nhsa.py --product 门冬氨酸钙片
  python fetch_nhsa.py --product 阿司匹林 --json
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

# 国家医保局药品目录查询
NHSA_DRUG_URL = "https://www.nhsa.gov.cn/col/col1748/index.html"
# 医保目录查询系统（2023版）
NHSA_QUERY_URL = "https://www.nhsa.gov.cn/module/download/downfile.jsp?classid=0&filename=1f4c7b2b4c2e4b8e9f3a5d6c7e8f9a0b.pdf"
# 实际可用的医保目录查询入口
NHSA_SEARCH_URL = "https://www.nhsa.gov.cn/col/col1748/index.html"

TIMEOUT = 30000
MAX_RETRIES = 3


def fetch_nhsa_data(product: str, wait_ms: int) -> dict:
    """采集国家医保局药品目录信息。"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ 缺少依赖: pip install playwright && playwright install chromium", file=sys.stderr)
        sys.exit(1)

    with sync_playwright() as p:
        browser, context = stealth_context(p, mobile=False)
        page = context.new_page()

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                page.goto(NHSA_SEARCH_URL, wait_until="domcontentloaded", timeout=TIMEOUT)
                page.wait_for_timeout(wait_ms)

                text = page.evaluate("() => document.body.innerText")
                title = page.title()

                # 尝试在搜索框输入产品名
                search_selectors = [
                    'input[placeholder*="搜索"]',
                    'input[placeholder*="请输入"]',
                    'input[type="search"]',
                    'input[type="text"]',
                ]
                searched = False
                for sel in search_selectors:
                    try:
                        page.wait_for_selector(sel, timeout=2000)
                        page.fill(sel, product)
                        human_delay(300, 600)
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
                    "query_date": datetime.now().strftime("%Y-%m-%d"),
                    "source": "国家医保局 nhsa.gov.cn",
                    "page_title": title,
                    "search_executed": searched,
                    "raw_text_preview": text[:4000],
                    "note": "医保类别（甲/乙类）需从页面内容中人工提取，或参考药智网的医保字段",
                }

            except Exception as e:
                if attempt < MAX_RETRIES:
                    print(f"⚠️  第 {attempt} 次请求失败，重试: {e}", file=sys.stderr)
                    time.sleep(2)
                else:
                    browser.close()
                    return {"success": False, "product": product, "error": str(e)}


def main() -> None:
    parser = argparse.ArgumentParser(description="采集国家医保局药品目录与医保类别")
    parser.add_argument("--product", required=True, help="产品名称")
    parser.add_argument("--wait", type=int, default=6000, help="页面等待时间（ms），默认 6000")
    parser.add_argument("--json", dest="output_json", action="store_true", help="输出 JSON 格式")
    args = parser.parse_args()

    print(f"🔍 查询国家医保局: {args.product}", file=sys.stderr)

    result = fetch_nhsa_data(args.product, args.wait)

    if result.get("success"):
        log_file = LOG_DIR / f"nhsa-{args.product}-{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
        log_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"📄 结果已保存: {log_file}", file=sys.stderr)

    if args.output_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if result["success"]:
            print(f"\n✅ 国家医保局查询成功")
            print(f"   产品: {result['product']}")
            print(f"   搜索已执行: {result['search_executed']}")
            print(f"\n   内容预览（前 500 字）:")
            print(f"   {result['raw_text_preview'][:500]}")
        else:
            print(f"\n❌ 查询失败: {result['error']}")


if __name__ == "__main__":
    main()
