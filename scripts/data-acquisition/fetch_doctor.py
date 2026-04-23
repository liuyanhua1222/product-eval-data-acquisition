"""
fetch_doctor.py — 采集抖音/视频号医生资源数据

鉴权模式: access-token（需要抖音已登录会话）
依赖: playwright（pip install playwright && playwright install chromium）

覆盖评估规则: K01/K02

说明:
  通过抖音站内搜索，按科室和疾病关键词检索医生账号，
  统计可合作医生数量、垂直科室医生数量、账号粉丝总量。
  K02（与内部医生库匹配度）依赖内部数据，本脚本仅输出
  抖音侧数据，匹配度判断需人工补充。

用法:
  python fetch_doctor.py --disease 黄褐斑 --department 皮肤科
  python fetch_doctor.py --disease 骨质疏松 --department 骨科 --platform douyin --json
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

DOUYIN_SEARCH_URL = "https://www.douyin.com/search/{keyword}?type=user"
TIMEOUT = 30000
MAX_RETRIES = 3
RETRY_INTERVAL = 2


def fetch_douyin_doctors(disease: str, department: str | None, wait_ms: int) -> dict:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ 缺少依赖: pip install playwright && playwright install chromium", file=sys.stderr)
        sys.exit(1)

    keywords = []
    if department:
        keywords.append(f"{department}医生")
    keywords.append(f"{disease}医生")
    if department:
        keywords.append(department)

    all_results = []

    with sync_playwright() as p:
        browser, context = stealth_context(p, mobile=False)

        cookie_count = load_cookies(context, "douyin")
        if cookie_count == 0:
            browser.close()
            return {
                "success": False,
                "error": "未找到抖音 Cookie，请先导入或登录",
                "action": "python scripts/platform-auth/login.py --import-cdp <cookies文件路径>",
            }

        page = context.new_page()

        for kw in keywords[:2]:
            url = DOUYIN_SEARCH_URL.format(keyword=kw)
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT)
                    page.wait_for_timeout(wait_ms)

                    if is_login_page(page.url):
                        browser.close()
                        return {
                            "success": False,
                            "error": "Cookie 已过期，请重新导入或登录",
                            "action": "python scripts/platform-auth/login.py --import-cdp <cookies文件路径>",
                        }

                    text = page.evaluate("() => document.body.innerText")
                    all_results.append({
                        "keyword": kw,
                        "url": url,
                        "raw_text_preview": text[:3000],
                    })
                    break
                except Exception as e:
                    if attempt < MAX_RETRIES:
                        print(f"⚠️  关键词 '{kw}' 第 {attempt} 次失败，重试: {e}", file=sys.stderr)
                        time.sleep(RETRY_INTERVAL)
                    else:
                        all_results.append({"keyword": kw, "error": str(e)})

        browser.close()

    return {
        "success": True,
        "disease": disease,
        "department": department,
        "platform": "douyin",
        "query_date": datetime.now().strftime("%Y-%m-%d"),
        "source": "抖音站内用户搜索 douyin.com/search",
        "keywords_searched": keywords[:2],
        "search_results": all_results,
        "k01_output": {
            "total_doctor_accounts": "待解析",
            "vertical_dept_doctors": "待解析",
            "disease_science_doctors": "待解析",
            "total_followers": "待解析",
            "note": "请根据 search_results 中的 raw_text_preview 人工统计或补充解析逻辑",
        },
        "k02_output": {
            "direct_match": "待补充",
            "need_expand": "待补充",
            "blank": "待补充",
            "missing_source": "需补充内部新媒体医生库",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="采集抖音/视频号医生资源数据")
    parser.add_argument("--disease", required=True, help="目标疾病/适应症，如'黄褐斑'")
    parser.add_argument("--department", help="垂直科室，如'皮肤科'")
    parser.add_argument(
        "--platform",
        choices=["douyin", "shipinhao", "all"],
        default="douyin",
        help="采集平台：douyin/shipinhao/all，默认 douyin（视频号暂不支持自动化）",
    )
    parser.add_argument("--wait", type=int, default=5000, help="页面等待时间（ms），默认 5000")
    parser.add_argument("--json", dest="output_json", action="store_true", help="输出 JSON 格式")
    args = parser.parse_args()

    if args.platform in ("shipinhao", "all"):
        print("⚠️  视频号暂不支持自动化采集，请手动查询", file=sys.stderr)
        if args.platform == "shipinhao":
            sys.exit(0)
        print("ℹ️  all 模式：执行抖音采集，视频号数据需手动补充", file=sys.stderr)

    print(f"🔍 采集医生资源: 疾病={args.disease}, 科室={args.department or '未指定'}", file=sys.stderr)

    result = fetch_douyin_doctors(args.disease, args.department, args.wait)

    if result.get("success"):
        log_file = LOG_DIR / f"doctor-{args.disease}-{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
        log_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"📄 结果已保存: {log_file}", file=sys.stderr)

    if args.output_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if result["success"]:
            print(f"\n✅ 医生资源采集完成")
            print(f"   疾病: {result['disease']}")
            print(f"   科室: {result.get('department', '未指定')}")
            print(f"   搜索关键词: {result['keywords_searched']}")
            print(f"\n   K01 输出（待解析）:")
            for k, v in result["k01_output"].items():
                if k != "note":
                    print(f"   - {k}: {v}")
            print(f"\n   ⚠️  {result['k01_output']['note']}")
            print(f"\n   K02 输出:")
            print(f"   - 缺失来源: {result['k02_output']['missing_source']}")
        else:
            print(f"\n❌ 采集失败: {result['error']}")
            if result.get("action"):
                print(f"   建议操作: {result['action']}")


if __name__ == "__main__":
    main()
