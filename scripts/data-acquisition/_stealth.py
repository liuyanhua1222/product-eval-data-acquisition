"""
_stealth.py — 共享 Playwright stealth 工具函数

参考 playwright-scraper-skill/scripts/playwright-stealth.js 的反爬技术：
- 隐藏 navigator.webdriver
- Mock window.chrome 对象
- Mock navigator.permissions
- iPhone / Desktop 真实 User-Agent
- 随机延迟模拟人类行为

所有 fetch_*.py 脚本通过 from _stealth import stealth_context, load_cookies 使用。
"""

import json
import os
import random
import time
from pathlib import Path

SESSION_DIR = Path(os.environ.get("SESSION_DIR", Path.home() / ".agent-browser" / "sessions"))

# 参考 playwright-scraper-skill 使用 iPhone UA（反爬效果更好）
IPHONE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)
DESKTOP_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# 参考 playwright-stealth.js 的完整 addInitScript 注入
STEALTH_INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => false });
window.chrome = { runtime: {} };
const _origPermQuery = window.navigator.permissions.query.bind(window.navigator.permissions);
window.navigator.permissions.query = (p) =>
    p.name === 'notifications'
        ? Promise.resolve({ state: Notification.permission })
        : _origPermQuery(p);
"""


def load_cookies(context, platform: str) -> int:
    """从文件加载 Cookie 到浏览器上下文，返回加载数量。"""
    cookie_path = SESSION_DIR / f"{platform}-cookies.json"
    if not cookie_path.exists():
        return 0
    try:
        cookies = json.loads(cookie_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return 0
    if cookies:
        context.add_cookies(cookies)
    return len(cookies)


def stealth_context(playwright, mobile: bool = False):
    """
    创建带完整 stealth 配置的 Playwright browser + context。

    参考 playwright-stealth.js：
    - iPhone UA（mobile=True）或 Desktop UA
    - 隐藏 webdriver、mock chrome 对象、mock permissions
    - 中文 locale

    返回 (browser, context) 元组，调用方负责 browser.close()。
    """
    browser = playwright.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
        ],
    )

    ua = IPHONE_UA if mobile else DESKTOP_UA
    viewport = {"width": 375, "height": 812} if mobile else {"width": 1440, "height": 900}

    context = browser.new_context(
        user_agent=ua,
        viewport=viewport,
        locale="zh-CN",
        extra_http_headers={
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        },
    )
    # 在页面加载前注入，确保 webdriver 标记在 JS 执行前已被覆盖
    context.add_init_script(STEALTH_INIT_SCRIPT)

    return browser, context


def human_delay(min_ms: int = 500, max_ms: int = 1500) -> None:
    """随机延迟，模拟人类操作节奏。"""
    time.sleep(random.uniform(min_ms / 1000, max_ms / 1000))


def is_login_page(url: str) -> bool:
    """判断当前 URL 是否为登录页。"""
    keywords = ["login", "signin", "passport", "sso", "auth", "account/login"]
    return any(k in url.lower() for k in keywords)
