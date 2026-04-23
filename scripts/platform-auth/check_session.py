"""
check_session.py — 检查各平台 Cookie 会话状态

鉴权模式: nologin
依赖: 无外部依赖

用法:
  python check_session.py                    # 检查所有平台
  python check_session.py --platform yaozh  # 检查指定平台
  python check_session.py --json            # 输出 JSON 格式
"""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

SESSION_DIR = Path(os.environ.get("SESSION_DIR", Path.home() / ".agent-browser" / "sessions"))

PLATFORMS = {
    "yaozh":    "药智网",
    "kaisi":    "开思CHIS",
    "douyin":   "抖音创作服务平台",
    "cma":      "中华医学会",
    "wanfang":  "万方数据",
    "cnki":     "知网CNKI",
    "nmpa":     "国家药监局（无需登录）",
    "nhsa":     "国家医保局（无需登录）",
}

NO_LOGIN_PLATFORMS = {"nmpa", "nhsa"}


def check_platform(platform: str) -> dict:
    """检查单个平台的会话状态，返回结构化结果。"""
    if platform in NO_LOGIN_PLATFORMS:
        return {
            "platform": platform,
            "name": PLATFORMS.get(platform, platform),
            "has_session": True,
            "login_required": False,
            "cookie_count": 0,
            "expires_at": None,
            "note": "公开数据，无需登录",
        }

    cookie_path = SESSION_DIR / f"{platform}-cookies.json"

    if not cookie_path.exists():
        return {
            "platform": platform,
            "name": PLATFORMS.get(platform, platform),
            "has_session": False,
            "login_required": True,
            "cookie_count": 0,
            "expires_at": None,
            "note": "未找到 Cookie 文件，需要登录",
        }

    try:
        cookies = json.loads(cookie_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return {
            "platform": platform,
            "name": PLATFORMS.get(platform, platform),
            "has_session": False,
            "login_required": True,
            "cookie_count": 0,
            "expires_at": None,
            "note": f"Cookie 文件损坏: {e}",
        }

    if not cookies:
        return {
            "platform": platform,
            "name": PLATFORMS.get(platform, platform),
            "has_session": False,
            "login_required": True,
            "cookie_count": 0,
            "expires_at": None,
            "note": "Cookie 文件为空，需要重新登录",
        }

    # 找最晚过期时间
    expires_timestamps = [
        c["expires"] for c in cookies if isinstance(c.get("expires"), (int, float)) and c["expires"] > 0
    ]
    expires_at = None
    if expires_timestamps:
        latest = max(expires_timestamps)
        expires_at = datetime.fromtimestamp(latest).strftime("%Y-%m-%d %H:%M")

    return {
        "platform": platform,
        "name": PLATFORMS.get(platform, platform),
        "has_session": True,
        "login_required": False,
        "cookie_count": len(cookies),
        "expires_at": expires_at,
        "note": "会话有效",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="检查各平台 Cookie 会话状态")
    parser.add_argument("--platform", help="平台标识（不传则检查所有平台）")
    parser.add_argument("--json", dest="output_json", action="store_true", help="输出 JSON 格式")
    args = parser.parse_args()

    platforms_to_check = [args.platform] if args.platform else list(PLATFORMS.keys())

    results = [check_platform(p) for p in platforms_to_check]

    if args.output_json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    # 人类可读格式
    print(f"\n{'平台':<10} {'名称':<20} {'状态':<8} {'Cookie数':<8} {'过期时间':<18} 备注")
    print("-" * 80)
    for r in results:
        status = "✅ 有效" if r["has_session"] else "❌ 无效"
        expires = r["expires_at"] or "-"
        count = str(r["cookie_count"]) if r["cookie_count"] > 0 else "-"
        print(f"{r['platform']:<10} {r['name']:<20} {status:<8} {count:<8} {expires:<18} {r['note']}")

    needs_login = [r["platform"] for r in results if r.get("login_required")]
    if needs_login:
        print(f"\n⚠️  需要登录的平台: {', '.join(needs_login)}")
        print("   执行: python scripts/platform-auth/login.py --platform <平台> --manual")


if __name__ == "__main__":
    main()
