"""
login.py — 登录数据平台并保存 Cookie 会话

鉴权模式: access-token（凭证通过 cms-auth-skills 获取）
依赖: playwright（pip install playwright && playwright install chromium）

用法:
  python login.py --platform yaozh --manual              # 手动登录（推荐）
  python login.py --platform yaozh --username 138xxx --password xxx
  python login.py --platform douyin --username 138xxx    # 短信登录（密码为验证码）
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

SESSION_DIR = Path(os.environ.get("SESSION_DIR", Path.home() / ".agent-browser" / "sessions"))
SESSION_DIR.mkdir(parents=True, exist_ok=True)

PLATFORM_CONFIGS = {
    "yaozh": {
        "name": "药智网",
        "login_url": "https://www.yaozh.com/login",
        "test_url": "https://db.yaozh.com/pijian",
        "test_text": "批准文号",
        "selectors": {
            "username": 'input[placeholder*="手机"]',
            "password": 'input[placeholder*="密码"]',
            "submit": 'button[type="submit"]',
        },
        "wait_after_login": 3000,
        "login_type": "password",
    },
    "kaisi": {
        "name": "开思CHIS",
        "login_url": "https://agent.sinohealth.com/chis",
        "test_url": "https://agent.sinohealth.com/chis",
        "test_text": "市场数据库",
        "selectors": {
            "username": 'input[type="text"]',
            "password": 'input[type="password"]',
            "submit": 'button[type="submit"]',
        },
        "wait_after_login": 5000,
        "login_type": "password",
    },
    "douyin": {
        "name": "抖音创作服务平台",
        "login_url": "https://creator.douyin.com/creator-micro/creator-count/arithmetic-index",
        "test_url": "https://creator.douyin.com/creator-micro/creator-count/arithmetic-index",
        "test_text": "关键词指数",
        "selectors": {
            "username": 'input[placeholder*="手机"]',
            "sms_button": 'button:has-text("获取验证码")',
            "code": 'input[placeholder*="验证码"]',
            "submit": 'button:has-text("登录")',
        },
        "wait_after_login": 3000,
        "login_type": "sms",
    },
    "cma": {
        "name": "中华医学会",
        "login_url": "https://www.cma.org.cn/col/col1702/index.html",
        "test_url": "https://www.cma.org.cn/",
        "test_text": "中华医学会",
        "selectors": {
            "username": 'input[placeholder*="手机"]',
            "password": 'input[placeholder*="密码"]',
            "submit": 'button[type="submit"]',
        },
        "wait_after_login": 3000,
        "login_type": "password",
    },
    "wanfang": {
        "name": "万方数据",
        "login_url": "https://s.wanfangdata.com.cn",
        "test_url": "https://s.wanfangdata.com.cn",
        "test_text": "万方数据",
        "selectors": {
            "username": 'input[placeholder*="手机"]',
            "password": 'input[placeholder*="密码"]',
            "submit": 'button[type="submit"]',
        },
        "wait_after_login": 3000,
        "login_type": "password",
    },
    "cnki": {
        "name": "知网CNKI",
        "login_url": "https://fsso.cnki.net",
        "test_url": "https://www.cnki.net",
        "test_text": "知网",
        "selectors": {
            "username": 'input[name="username"]',
            "password": 'input[name="password"]',
            "submit": 'button[type="submit"]',
        },
        "wait_after_login": 3000,
        "login_type": "password",
    },
}


def save_cookies(context, platform: str) -> int:
    """保存 Cookie 到文件，返回 Cookie 数量。"""
    cookie_path = SESSION_DIR / f"{platform}-cookies.json"
    cookies = context.cookies()
    cookie_path.write_text(json.dumps(cookies, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(cookies)


def is_logged_in(page, config: dict) -> bool:
    """检测页面是否已处于登录状态。"""
    try:
        url = page.url
        if "login" in url.lower() or "signin" in url.lower():
            return False
        has_login_form = page.evaluate("""() => {
            return !!(
                document.querySelector('input[type="password"]:not([style*="hidden"])') ||
                document.querySelector('input[placeholder*="密码"]') ||
                document.querySelector('input[placeholder*="账号"]')
            );
        }""")
        if has_login_form:
            return False
        page_text = page.evaluate("() => document.body.innerText")
        login_keywords = ["退出", "退出登录", "我的账户", "个人中心", "账号设置", "VIP"]
        return any(kw in page_text for kw in login_keywords)
    except Exception:
        return False


def login_manual(platform: str, config: dict) -> dict:
    """手动登录：打开浏览器窗口，等待用户完成登录，自动检测成功后保存 Cookie。"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ 缺少依赖: pip install playwright && playwright install chromium", file=sys.stderr)
        sys.exit(1)

    print(f"\n🖥️  手动登录 - {config['name']}")
    print("   支持：账号密码、短信验证码、微信扫码、App 扫码等任意方式")
    print("   浏览器将打开登录页，完成登录后自动检测并保存 Cookie\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => false})")

        page = context.new_page()
        page.goto(config["login_url"], wait_until="domcontentloaded", timeout=30000)
        print(f"✅ 已打开登录页: {config['login_url']}")

        if is_logged_in(page, config):
            print("ℹ️  检测到已登录（Cookie 未过期），直接保存...")
        else:
            print("\n⏳ 等待你完成登录（最多 5 分钟）...")
            max_attempts = 150
            for attempt in range(max_attempts):
                time.sleep(2)
                if is_logged_in(page, config):
                    print("\n✅ 检测到登录成功！")
                    break
                if attempt % 15 == 14:
                    elapsed = (attempt + 1) * 2
                    print(f"   ⏳ 已等待 {elapsed // 60} 分 {elapsed % 60} 秒，可继续操作浏览器...")
            else:
                print("\n⚠️  等待超时，按回车继续（如已完成登录）...")
                input()

        count = save_cookies(context, platform)
        browser.close()

    return {
        "platform": platform,
        "success": True,
        "cookie_count": count,
        "cookie_path": str(SESSION_DIR / f"{platform}-cookies.json"),
    }


def login_password(platform: str, config: dict, username: str, password: str) -> dict:
    """自动化填表登录（账号密码）。"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ 缺少依赖: pip install playwright && playwright install chromium", file=sys.stderr)
        sys.exit(1)

    print(f"\n🔐 自动登录 - {config['name']}")

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

        page = context.new_page()
        page.goto(config["login_url"], wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)

        sel = config["selectors"]
        if sel.get("username") and username:
            page.fill(sel["username"], username)
        if sel.get("password") and password:
            page.fill(sel["password"], password)
        if sel.get("submit"):
            page.click(sel["submit"])

        page.wait_for_timeout(config["wait_after_login"])

        # 验证登录结果
        try:
            page.goto(config["test_url"], wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(2000)
            content = page.evaluate("() => document.body.innerText")
            success = config["test_text"] in content
        except Exception:
            success = False

        count = save_cookies(context, platform)
        browser.close()

    if not success:
        print(f"⚠️  登录结果不确定，页面未包含预期内容 '{config['test_text']}'")

    return {
        "platform": platform,
        "success": success,
        "cookie_count": count,
        "cookie_path": str(SESSION_DIR / f"{platform}-cookies.json"),
    }


def login_sms(platform: str, config: dict, username: str, code: str | None) -> dict:
    """短信验证码登录（抖音等）。"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ 缺少依赖: pip install playwright && playwright install chromium", file=sys.stderr)
        sys.exit(1)

    print(f"\n📱 短信登录 - {config['name']}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,  # 短信登录需要可见窗口
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )

        page = context.new_page()
        page.goto(config["login_url"], wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)

        sel = config["selectors"]
        if sel.get("username") and username:
            page.fill(sel["username"], username)
        if sel.get("sms_button"):
            page.click(sel["sms_button"])
            print("   已点击获取验证码")

        if code:
            page.wait_for_timeout(3000)
            if sel.get("code"):
                page.fill(sel["code"], code)
            if sel.get("submit"):
                page.click(sel["submit"])
        else:
            print("   请在浏览器窗口中完成验证码输入，然后按回车继续...")
            input()

        page.wait_for_timeout(config["wait_after_login"])

        count = save_cookies(context, platform)
        browser.close()

    return {
        "platform": platform,
        "success": True,
        "cookie_count": count,
        "cookie_path": str(SESSION_DIR / f"{platform}-cookies.json"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="登录数据平台并保存 Cookie 会话")
    parser.add_argument("--platform", required=True, help="平台标识（yaozh/kaisi/douyin/cma/wanfang/cnki）")
    parser.add_argument("--username", help="账号或手机号")
    parser.add_argument("--password", help="密码或短信验证码")
    parser.add_argument("--manual", action="store_true", help="手动登录模式（打开浏览器窗口）")
    parser.add_argument("--json", dest="output_json", action="store_true", help="输出 JSON 格式")
    args = parser.parse_args()

    platform = args.platform.lower()
    if platform not in PLATFORM_CONFIGS:
        print(f"❌ 未知平台: {platform}", file=sys.stderr)
        print(f"   支持的平台: {', '.join(PLATFORM_CONFIGS.keys())}", file=sys.stderr)
        sys.exit(1)

    config = PLATFORM_CONFIGS[platform]

    if args.manual:
        result = login_manual(platform, config)
    elif config["login_type"] == "sms":
        if not args.username:
            print("❌ 短信登录需要 --username（手机号）", file=sys.stderr)
            sys.exit(1)
        result = login_sms(platform, config, args.username, args.password)
    else:
        if not args.username or not args.password:
            print("❌ 密码登录需要 --username 和 --password", file=sys.stderr)
            sys.exit(1)
        result = login_password(platform, config, args.username, args.password)

    if args.output_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        status = "✅ 成功" if result["success"] else "⚠️  不确定"
        print(f"\n{status} 登录 {config['name']}")
        print(f"   Cookie 数量: {result['cookie_count']}")
        print(f"   保存路径: {result['cookie_path']}")


if __name__ == "__main__":
    main()
