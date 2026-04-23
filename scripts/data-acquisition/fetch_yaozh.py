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
import os
import sys
import time
from datetime import datetime
from pathlib import Path

SESSION_DIR = Path(os.environ.get("SESSION_DIR", Path.home() / ".agent-browser" / "sessions"))
LOG_DIR = Path(".cms-log/log/product-eval-data-acquisition")
LOG_DIR.mkdir(parents=True, exist_ok=True)

SEARCH_URL = "https://db.yaozh.com/pijian?comprehensivesearchcontent={keyword}"
TIMEOUT = 30000
MAX_RETRIES = 3
RETRY_INTERVAL = 2


def load_cookies(context, platform: str) -> int:
    """从文件加载 Cookie 到浏览器上下文，返回加载数量。"""
    cookie_path = SESSION_DIR / f"{platform}-cookies.json"
    if not cookie_path.exists():
        return 0
    cookies = json.loads(cookie_path.read_text(encoding="utf-8"))
    if cookies:
        context.add_cookies(cookies)
    return len(cookies)


def fetch_page(url: str, platform: str, wait_ms: int) -> dict:
    """使用已登录会话抓取页面，返回页面文本和标题。"""
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
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
            ),
            viewport={"width": 375, "height": 812},
        )
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => false})")

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
    """从页面文本中解析批文记录（简单文本解析，实际可按页面结构优化）。"""
    records = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    # 药智网批文页面的典型字段标记
    field_markers = ["批准文号", "企业名称", "剂型", "规格", "批准日期", "医保类别", "状态"]
    current = {}

    for line in lines:
        for marker in field_markers:
            if line.startswith(marker) and "：" in line:
                key = marker
                value = line.split("：", 1)[1].strip()
                current[key] = value
                break
        # 简单启发：遇到新批准文号时保存上一条
        if line.startswith("国药准字") or line.startswith("H") and len(line) == 10:
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

    # 检查是否跳转到登录页
    if "login" in page_data["url"].lower():
        result = {
            "success": False,
            "error": "Cookie 已过期，请重新登录",
            "action": "python scripts/platform-auth/login.py --platform yaozh --manual",
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

        # 写入日志
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
            print(f"   查询日期: {result['query_date']}")
            if result["records"]:
                print(f"\n   前 3 条记录:")
                for r in result["records"][:3]:
                    print(f"   - {r}")
        else:
            print(f"\n❌ 查询失败: {result['error']}")
            print(f"   建议操作: {result.get('action', '')}")


if __name__ == "__main__":
    main()
