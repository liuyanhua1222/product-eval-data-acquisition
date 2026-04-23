"""
fetch_yaozh.py — 采集药智网批文与说明书数据

鉴权模式: access-token（需要药智网已登录会话）
依赖: playwright（pip install playwright && playwright install chromium）

覆盖评估规则: A00/A01/A04/A08/A09/A10/B01/B02/F01/F02

用法:
  python fetch_yaozh.py --product 门冬氨酸钙片
  python fetch_yaozh.py --product 阿司匹林 --approval-number H10900001
  python fetch_yaozh.py --product 阿司匹林 --wait 8000 --json
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _stealth import load_cookies, stealth_context, is_login_page

LOG_DIR = Path(".cms-log/log/product-eval-data-acquisition")
LOG_DIR.mkdir(parents=True, exist_ok=True)

SEARCH_URL = "https://db.yaozh.com/pijian?comprehensivesearchcontent={keyword}"
TIMEOUT = 30000
MAX_RETRIES = 3
RETRY_INTERVAL = 2


def fetch_page(url: str, platform: str, wait_ms: int) -> dict:
    """使用已登录会话抓取页面，返回页面文本和标题。"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ 缺少依赖: pip install playwright && playwright install chromium", file=sys.stderr)
        sys.exit(1)

    with sync_playwright() as p:
        # 药智网用 iPhone UA，参考 playwright-stealth.js
        browser, context = stealth_context(p, mobile=True)

        cookie_count = load_cookies(context, platform)
        if cookie_count == 0:
            print("⚠️  未找到药智网 Cookie，部分数据可能受限", file=sys.stderr)

        page = context.new_page()

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT)
                page.wait_for_timeout(wait_ms)
                status = response.status if response else 0
                text = page.evaluate("() => document.body.innerText")
                title = page.title()
                html = page.content()
                browser.close()
                return {"status": status, "text": text, "title": title, "html": html, "url": page.url}
            except Exception as e:
                if attempt < MAX_RETRIES:
                    print(f"⚠️  第 {attempt} 次请求失败，{RETRY_INTERVAL}s 后重试: {e}", file=sys.stderr)
                    time.sleep(RETRY_INTERVAL)
                else:
                    browser.close()
                    raise


def parse_approval_records(text: str) -> list[dict]:
    """从页面文本中解析批文记录。"""
    records = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    field_markers = ["批准文号", "企业名称", "剂型", "规格", "批准日期", "医保类别", "状态"]
    current = {}

    for line in lines:
        for marker in field_markers:
            if line.startswith(marker) and "：" in line:
                current[marker] = line.split("：", 1)[1].strip()
                break
        if line.startswith("国药准字") or (line.startswith("H") and len(line) == 10):
            if current:
                records.append(current)
            current = {"批准文号": line}

    if current:
        records.append(current)

    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="采集药智网批文与说明书数据")
    parser.add_argument("--product", required=True, help="产品名称或 API 名称")
    parser.add_argument("--approval-number", help="批准文号（有则优先精确查询）")
    parser.add_argument("--wait", type=int, default=5000, help="页面等待时间（ms），默认 5000")
    parser.add_argument("--json", dest="output_json", action="store_true", help="输出 JSON 格式")
    args = parser.parse_args()

    keyword = args.approval_number or args.product
    url = SEARCH_URL.format(keyword=keyword)

    print(f"🔍 查询药智网: {keyword}", file=sys.stderr)

    page_data = fetch_page(url, "yaozh", args.wait)

    if is_login_page(page_data["url"]):
        result = {
            "success": False,
            "error": "Cookie 已过期，请重新导入或登录",
            "action": "python scripts/platform-auth/login.py --import-cdp <cookies文件路径>",
        }
    else:
        records = parse_approval_records(page_data["text"])
        result = {
            "success": True,
            "product": args.product,
            "query_keyword": keyword,
            "query_url": url,
            "query_date": datetime.now().strftime("%Y-%m-%d"),
            "source": "药智网 db.yaozh.com",
            "record_count": len(records),
            "records": records,
            "raw_text_preview": page_data["text"][:2000],
        }
        log_file = LOG_DIR / f"yaozh-{args.product}-{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
        log_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"📄 结果已保存: {log_file}", file=sys.stderr)

    if args.output_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if result["success"]:
            print(f"\n✅ 药智网查询成功")
            print(f"   产品: {result['product']}")
            print(f"   记录数: {result['record_count']}")
            if result["records"]:
                print(f"\n   前 3 条记录:")
                for r in result["records"][:3]:
                    print(f"   - {r}")
        else:
            print(f"\n❌ 查询失败: {result['error']}")
            print(f"   建议操作: {result.get('action', '')}")


if __name__ == "__main__":
    main()
