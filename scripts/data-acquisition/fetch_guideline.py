"""
fetch_guideline.py — 采集中华医学会及行业学会临床指南/专家共识

鉴权模式: nologin（大部分指南公开）/ access-token（全文下载需登录）
依赖: playwright（pip install playwright && playwright install chromium）

覆盖评估规则: E01/E02/I06/I07

说明:
  查询来源：
  - 中华医学会（cma.org.cn）：内科/外科/皮肤科/骨科等各专科指南
  - 中华皮肤科杂志（cjd.org.cn）：皮肤科专科指南
  - 中国医师协会（cmda.net）：各专科诊疗规范
  - 各专科学会官网（骨质疏松学会、心血管学会等）

  用于判断：
  - E01：产品/API 是否被一线指南推荐
  - I06：本品在指南中的推荐顺位相较竞品

用法:
  python fetch_guideline.py --disease 骨质疏松 --drug 钙剂
  python fetch_guideline.py --disease 黄褐斑 --source cma --json
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

# 各学会指南查询入口
SOURCE_CONFIGS = {
    "cma": {
        "name": "中华医学会",
        "search_url": "https://www.cma.org.cn/col/col1702/index.html",
        "note": "中华医学会各专科分会指南",
    },
    "cjd": {
        "name": "中华皮肤科杂志",
        "search_url": "https://www.cjd.org.cn/",
        "note": "皮肤科专科指南与共识",
    },
    "cmda": {
        "name": "中国医师协会",
        "search_url": "https://www.cmda.net/",
        "note": "各专科诊疗规范",
    },
    "dxy_guide": {
        "name": "丁香园临床指南",
        "search_url": "https://guide.dxy.cn/article/search?keyword={keyword}",
        "note": "丁香园整合的临床指南数据库（推荐，覆盖最全）",
    },
}

TIMEOUT = 30000
MAX_RETRIES = 3


def fetch_guideline_data(disease: str, drug: str | None, source: str, wait_ms: int) -> dict:
    """采集指定来源的临床指南数据。"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ 缺少依赖: pip install playwright && playwright install chromium", file=sys.stderr)
        sys.exit(1)

    config = SOURCE_CONFIGS.get(source, SOURCE_CONFIGS["dxy_guide"])
    keyword = f"{disease} {drug}" if drug else disease

    # 丁香园指南支持直接关键词搜索
    if source == "dxy_guide":
        url = config["search_url"].format(keyword=keyword)
    else:
        url = config["search_url"]

    with sync_playwright() as p:
        browser, context = stealth_context(p, mobile=False)
        load_cookies(context, source)
        page = context.new_page()

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT)
                page.wait_for_timeout(wait_ms)

                # 非丁香园来源，尝试站内搜索
                if source != "dxy_guide":
                    search_selectors = [
                        'input[placeholder*="搜索"]',
                        'input[placeholder*="关键词"]',
                        'input[type="search"]',
                        'input[type="text"]',
                    ]
                    for sel in search_selectors:
                        try:
                            page.wait_for_selector(sel, timeout=2000)
                            page.fill(sel, keyword)
                            human_delay(300, 600)
                            page.keyboard.press("Enter")
                            page.wait_for_timeout(wait_ms)
                            break
                        except Exception:
                            continue

                text = page.evaluate("() => document.body.innerText")
                title = page.title()

                browser.close()
                return {
                    "success": True,
                    "disease": disease,
                    "drug": drug,
                    "keyword": keyword,
                    "source": source,
                    "source_name": config["name"],
                    "query_url": url,
                    "query_date": datetime.now().strftime("%Y-%m-%d"),
                    "page_title": title,
                    "raw_text_preview": text[:4000],
                    "note": config["note"],
                }

            except Exception as e:
                if attempt < MAX_RETRIES:
                    print(f"⚠️  第 {attempt} 次请求失败，重试: {e}", file=sys.stderr)
                    time.sleep(2)
                else:
                    browser.close()
                    return {"success": False, "disease": disease, "error": str(e)}


def main() -> None:
    parser = argparse.ArgumentParser(description="采集中华医学会及行业学会临床指南/专家共识")
    parser.add_argument("--disease", required=True, help="目标疾病，如'骨质疏松'")
    parser.add_argument("--drug", help="目标药物/API，如'钙剂'（可选，不传则只搜疾病）")
    parser.add_argument(
        "--source",
        choices=list(SOURCE_CONFIGS.keys()),
        default="dxy_guide",
        help=f"数据来源：{'/'.join(SOURCE_CONFIGS.keys())}，默认 dxy_guide（推荐）",
    )
    parser.add_argument("--wait", type=int, default=6000, help="页面等待时间（ms），默认 6000")
    parser.add_argument("--json", dest="output_json", action="store_true", help="输出 JSON 格式")
    args = parser.parse_args()

    print(f"🔍 查询临床指南 [{args.source}]: {args.disease} {args.drug or ''}", file=sys.stderr)

    result = fetch_guideline_data(args.disease, args.drug, args.source, args.wait)

    if result.get("success"):
        fname = f"guideline-{args.disease}-{args.source}-{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
        log_file = LOG_DIR / fname
        log_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"📄 结果已保存: {log_file}", file=sys.stderr)

    if args.output_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if result["success"]:
            print(f"\n✅ 指南查询成功")
            print(f"   来源: {result['source_name']}")
            print(f"   关键词: {result['keyword']}")
            print(f"\n   内容预览（前 500 字）:")
            print(f"   {result['raw_text_preview'][:500]}")
        else:
            print(f"\n❌ 查询失败: {result['error']}")


if __name__ == "__main__":
    main()
