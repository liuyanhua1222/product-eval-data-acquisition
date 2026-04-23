# platform-auth — 平台登录与会话管理

## 模块说明

管理各数据平台的登录态与 Cookie 持久化。支持自动化填表登录、手动登录检测、Cookie 注入三种方式。

---

## 适用场景

- 首次使用前确认各平台登录状态
- Cookie 过期后重新登录
- 切换账号时清除旧会话

---

## 支持的平台

| 平台标识 | 平台名称 | 登录方式 | 是否必须 |
|---------|---------|---------|---------|
| `yaozh` | 药智网 | 账号密码 / 手机验证码 | 推荐 |
| `kaisi` | 开思CHIS | 账号密码 / 微信扫码 | 必须（H 模块） |
| `douyin` | 抖音创作服务平台 | 手机短信验证码 | 推荐（C03/B03） |
| `cma` | 中华医学会 | 账号密码 | 可选 |
| `wanfang` | 万方数据 | 账号密码 | 可选 |
| `cnki` | 知网CNKI | 账号密码 | 可选 |
| `nmpa` | 国家药监局 | 无需登录 | — |
| `nhsa` | 国家医保局 | 无需登录 | — |

---

## 动作列表

### check_session — 检查会话状态

**鉴权模式**: `nologin`

**输入**:

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| `--platform` | string | 否 | 平台标识，不传则检查所有平台 |

**输出**:

```json
{
  "platform": "yaozh",
  "has_session": true,
  "cookie_count": 12,
  "expires_at": "2026-05-22"
}
```

---

### login — 登录平台并保存 Cookie

**鉴权模式**: `access-token`（通过 `cms-auth-skills` 获取凭证）

**输入**:

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| `--platform` | string | 是 | 平台标识 |
| `--username` | string | 条件必须 | 账号/手机号（手动登录时不需要） |
| `--password` | string | 条件必须 | 密码/验证码（手动登录时不需要） |
| `--manual` | flag | 否 | 开启手动登录模式（打开浏览器窗口） |

**输出**:

```json
{
  "platform": "yaozh",
  "success": true,
  "cookie_count": 12,
  "cookie_path": "~/.agent-browser/sessions/yaozh-cookies.json"
}
```

---

### clear_session — 清除会话

**鉴权模式**: `nologin`

**输入**:

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| `--platform` | string | 是 | 平台标识，传 `all` 清除所有 |

**输出**:

```json
{
  "platform": "yaozh",
  "cleared": true
}
```

---

## 约束

- Cookie 文件保存在 `~/.agent-browser/sessions/`，不写入 Skill 包目录
- 凭证（账号密码）通过 `cms-auth-skills` 获取，不在本模块存储
- 手动登录模式（`--manual`）会打开可见浏览器窗口，需要用户在窗口中完成操作
