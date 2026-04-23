# platform-auth 脚本索引

## 脚本清单

| 脚本 | 用途 | 鉴权模式 |
|------|------|---------|
| `check_session.py` | 检查各平台 Cookie 会话状态 | nologin |
| `login.py` | 登录平台并保存 Cookie | access-token |
| `clear_session.py` | 清除平台 Cookie 会话 | nologin |

---

## 鉴权前置条件

- `check_session.py` 和 `clear_session.py` 无需鉴权，直接运行
- `login.py` 需要平台账号凭证，通过 `cms-auth-skills` 获取

---

## 运行方式

```bash
# 检查所有平台状态
python scripts/platform-auth/check_session.py

# 检查指定平台
python scripts/platform-auth/check_session.py --platform yaozh

# 手动登录（推荐，支持扫码/短信/账号密码）
python scripts/platform-auth/login.py --platform yaozh --manual

# 自动化登录（账号密码）
python scripts/platform-auth/login.py --platform yaozh --username 138xxx --password xxx

# 短信登录（抖音）
python scripts/platform-auth/login.py --platform douyin --username 138xxx

# 手动登录（小红书/京东/天猫/美团/饿了么当前仅支持手动）
python scripts/platform-auth/login.py --platform xiaohongshu --manual

# 清除指定平台会话
python scripts/platform-auth/clear_session.py --platform yaozh

# 清除所有会话
python scripts/platform-auth/clear_session.py --platform all
```

---

## 返回说明

所有脚本支持 `--json` 参数输出结构化 JSON，便于 AI 解析。

```json
// check_session.py 输出示例
{
  "platform": "yaozh",
  "name": "药智网",
  "has_session": true,
  "login_required": false,
  "cookie_count": 12,
  "expires_at": "2026-05-22 10:30",
  "note": "会话有效"
}
```

---

## 依赖

- `check_session.py`：无外部依赖（Python 标准库）
- `login.py`：需要 `playwright`（`pip install playwright && playwright install chromium`）
- `clear_session.py`：无外部依赖（Python 标准库）
- 小红书、京东、天猫、美团、饿了么当前仅支持 `--manual` 手动登录或 `--import-cdp` 导入 Cookie
