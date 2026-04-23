"""
clear_session.py — 清除平台 Cookie 会话

鉴权模式: nologin
依赖: 无外部依赖

用法:
  python clear_session.py --platform yaozh   # 清除指定平台
  python clear_session.py --platform all     # 清除所有平台
  python clear_session.py --platform yaozh --json
"""

import argparse
import json
import os
from pathlib import Path

SESSION_DIR = Path(os.environ.get("SESSION_DIR", Path.home() / ".agent-browser" / "sessions"))

ALL_PLATFORMS = [
    "yaozh",
    "kaisi",
    "douyin",
    "xiaohongshu",
    "jd",
    "tmall",
    "meituan",
    "eleme",
    "dingxiangyuan",
    "cma",
    "wanfang",
    "cnki",
]


def clear_platform(platform: str) -> dict:
    """清除指定平台的 Cookie 文件。"""
    cookie_path = SESSION_DIR / f"{platform}-cookies.json"
    if cookie_path.exists():
        try:
            cookie_path.unlink()
        except PermissionError as e:
            return {"platform": platform, "cleared": False, "note": f"无权限删除会话文件: {e}"}
        return {"platform": platform, "cleared": True, "note": "会话已清除"}
    return {"platform": platform, "cleared": False, "note": "无会话可清除"}


def main() -> None:
    parser = argparse.ArgumentParser(description="清除平台 Cookie 会话")
    parser.add_argument("--platform", required=True, help="平台标识，传 all 清除所有平台")
    parser.add_argument("--json", dest="output_json", action="store_true", help="输出 JSON 格式")
    args = parser.parse_args()

    platforms = ALL_PLATFORMS if args.platform.lower() == "all" else [args.platform.lower()]

    # 清除 all 时需要确认
    if args.platform.lower() == "all" and not args.output_json:
        confirm = input(f"⚠️  将清除所有 {len(platforms)} 个平台的会话，确认？(y/N) ").strip().lower()
        if confirm != "y":
            print("已取消")
            return

    results = [clear_platform(p) for p in platforms]

    if args.output_json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    for r in results:
        icon = "✅" if r["cleared"] else "ℹ️ "
        print(f"{icon} {r['platform']}: {r['note']}")


if __name__ == "__main__":
    main()
