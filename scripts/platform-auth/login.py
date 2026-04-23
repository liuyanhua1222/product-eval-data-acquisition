"""
login.py — 登录数据平台并保存 Cookie 会话

鉴权模式: access-token（凭证通过 cms-auth-skills 获取）
依赖: playwright（pip install playwright && playwright install chromium）

用法:
  python login.py --platform yaozh --manual              # 手动登录（推荐）
  python login.py --platform yaozh --username 138xxx --password xxx
  python login.py --platform douyin --username 138xxx    # 短信登录（密码为验证码）
  python login.py --import-cdp /path/to/cookies-cdp-domain.json  # 从 CDP 域名分组文件批量导入
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
    "xiaohongshu": {
        "name": "小红书",
        "login_url": "https://www.xiaohongshu.com/explore",
        "test_url": "https://www.xiaohongshu.com/explore",
        "test_text": "小红书",
        "selectors": {},
        "wait_after_login": 5000,
        "login_type": "manual_only",
    },
    "jd": {
        "name": "京东",
        "login_url": "https://passport.jd.com/new/login.aspx",
        "test_url": "https://www.jd.com/",
        "test_text": "京东",
        "selectors": {},
        "wait_after_login": 5000,
        "login_type": "manual_only",
    },
    "tmall": {
        "name": "天猫",
        "login_url": "https://login.tmall.com/",
        "test_url": "https://www.tmall.com/",
        "test_text": "天猫",
        "selectors": {},
        "wait_after_login": 5000,
        "login_type": "manual_only",
    },
    "meituan": {
        "name": "美团",
        "login_url": "https://passport.meituan.com/account/unitivelogin",
        "test_url": "https://www.meituan.com/",
        "test_text": "美团",
        "selectors": {},
        "wait_after_login": 5000,
        "login_type": "manual_only",
    },
    "eleme": {
        "name": "饿了么",
        "login_url": "https://h5.ele.me/login/",
        "test_url": "https://h5.ele.me/",
        "test_text": "饿了么",
        "selectors": {},
        "wait_after_login": 5000,
        "login_type": "manual_only",
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
    parser.add_argument("--platform", help="平台标识（yaozh/kaisi/douyin/xiaohongshu/jd/tmall/meituan/cma/wanfang/cnki）")
    parser.add_argument("--username", help="账号或手机号")
    parser.add_argument("--password", help="密码或短信验证码")
    parser.add_argument("--manual", action="store_true", help="手动登录模式（打开浏览器窗口）")
    parser.add_argument(
        "--import-cdp",
        metavar="FILE",
        help="从 CDP 域名分组格式的 JSON 文件批量导入 Cookie（如 cookies-cdp-domain.json）",
    )
    parser.add_argument("--json", dest="output_json", action="store_true", help="输出 JSON 格式")
    args = parser.parse_args()

    # ── CDP 批量导入模式 ────────────────────────────────────────────────────
    if args.import_cdp:
        _import_cdp_cookies(args.import_cdp, args.output_json)
        return

    # ── 单平台登录模式 ──────────────────────────────────────────────────────
    if not args.platform:
        parser.error("请指定 --platform 或 --import-cdp")

    platform = args.platform.lower()
    if platform not in PLATFORM_CONFIGS:
        print(f"❌ 未知平台: {platform}", file=sys.stderr)
        print(f"   支持的平台: {', '.join(PLATFORM_CONFIGS.keys())}", file=sys.stderr)
        sys.exit(1)

    config = PLATFORM_CONFIGS[platform]

    if args.manual:
        result = login_manual(platform, config)
    elif config["login_type"] == "manual_only":
        print(f"❌ {config['name']} 仅支持 --manual 手动登录或 --import-cdp 导入 Cookie", file=sys.stderr)
        sys.exit(1)
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


# ── CDP 域名分组格式批量导入 ────────────────────────────────────────────────

# 域名 → 平台标识映射
_DOMAIN_TO_PLATFORM = {
    "yaozh.com":          "yaozh",
    "sinohealth.com":     "kaisi",
    "jd.com":             "jd",
    "tmall.com":          "tmall",
    "taobao.com":         "tmall",        # 天猫/淘宝共用同一 Cookie
    "douyin.com":         "douyin",
    "creator.douyin.com": "douyin",       # creator 子域与主域合并
    "wanfangdata.com.cn": "wanfang",
    "cnki.net":           "cnki",
    "xiaohongshu.com":    "xiaohongshu",
    "xhscdn.com":         "xiaohongshu",  # 小红书 CDN 域
    "meituan.com":        "meituan",
    "ele.me":             "eleme",
    "dxy.cn":             "dingxiangyuan",
    "dxy.com":            "dingxiangyuan",
    "cma.org.cn":         "cma",
}

# 公开平台：无需 Cookie，跳过时给出正确提示
_PUBLIC_DOMAINS = {
    "nmpa.gov.cn":             "国家药监局（公开数据，无需 Cookie）",
    "pubmed.ncbi.nlm.nih.gov": "PubMed（公开 API，无需 Cookie）",
    "nhsa.gov.cn":             "国家医保局（公开数据，无需 Cookie）",
}


def _import_cdp_cookies(cdp_file: str, output_json: bool = False) -> None:
    """
    从 CDP 域名分组格式的 JSON 文件批量导入 Cookie。

    文件格式：{ "domain.com": [ {name, value, domain, path, ...}, ... ], ... }
    输出格式：~/.agent-browser/sessions/<platform>-cookies.json（Playwright flat list）
    """
    cdp_path = Path(cdp_file)
    if not cdp_path.exists():
        print(f"❌ 文件不存在: {cdp_file}", file=sys.stderr)
        sys.exit(1)

    try:
        data: dict = json.loads(cdp_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"❌ 读取文件失败: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(data, dict):
        print("❌ 文件格式错误：顶层应为域名→Cookie列表的对象", file=sys.stderr)
        sys.exit(1)

    platform_cookies: dict[str, list] = {}
    results = []

    for domain, cookies in data.items():
        if domain in _PUBLIC_DOMAINS:
            results.append({"domain": domain, "status": "skipped", "reason": _PUBLIC_DOMAINS[domain]})
            print(f"ℹ️  {domain} → {_PUBLIC_DOMAINS[domain]}")
            continue

        platform = _DOMAIN_TO_PLATFORM.get(domain)
        if not platform:
            results.append({"domain": domain, "status": "skipped", "reason": "未知域名，未在映射表中"})
            print(f"⚠️  {domain} → 未知域名，跳过（如需支持请更新 _DOMAIN_TO_PLATFORM）")
            continue

        if platform not in platform_cookies:
            platform_cookies[platform] = []
        platform_cookies[platform].extend(cookies)

    # 写入各平台文件，按 (name, domain, path) 去重
    for platform, cookies in platform_cookies.items():
        seen: dict[tuple, dict] = {}
        for c in cookies:
            key = (c.get("name"), c.get("domain"), c.get("path"))
            seen[key] = c
        deduped = list(seen.values())

        out = SESSION_DIR / f"{platform}-cookies.json"
        out.write_text(json.dumps(deduped, ensure_ascii=False, indent=2), encoding="utf-8")
        results.append({"platform": platform, "status": "imported", "cookie_count": len(deduped), "path": str(out)})
        print(f"✅ {platform}: {len(deduped)} cookies → {out}")

    print(f"\n导入完成：{len(platform_cookies)} 个平台")

    if output_json:
        print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
