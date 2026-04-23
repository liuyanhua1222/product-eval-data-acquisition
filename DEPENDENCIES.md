# product-eval-data-acquisition Skill 依赖说明

> 本文件列出该Skill正常运行所需的全部依赖，包括平台账号、软件环境、数据源权限。任何使用者需在正式运行前自行确认以下各项已就绪。

---

## 一、平台账号依赖

以下平台需要**有效账号**才能访问全部数据功能，星光标(⭐)表示推荐有账号但部分数据可免登录访问：

| 平台 | 必须/可选 | 账号类型 | 用途说明 | 获取方式 |
|------|---------|---------|---------|---------|
| ⭐ **药智网** | 推荐有账号 | 免费/付费VIP | 批文检索、说明书、医保类别；VIP可查电商销售数据 | db.yaozh.com |
| ⭐ **开思CHIS** | 推荐有账号 | VIP付费账号 | 零售市场数据、B2C规模、品牌份额、Top3数据；无账号则H模块全部无法完成 | agent.sinohealth.com |
| ⭐ **京东** | 推荐有账号 | 免费账号 | 电商价格、评价数、店铺数；无账号可访问但数据有限 | jd.com |
| ⭐ **天猫/淘宝** | 推荐有账号 | 免费账号 | B2C价格对比；无账号可访问但数据有限 | tmall.com |
| ⭐ **美团** | 可选 | 免费 | O2O蜂窝覆盖率、付费推广状态；可替代饿了么 | meituan.com |
| **抖音创作服务平台** | 可选（有则更好） | 免费账号 | 抖音关键词指数查询；无账号则C03/J02无法完成 | creator.douyin.com |
| **NMPA国家药监局** | 推荐有账号 | 免费 | 批文交叉验证；无需账号 | nmpa.gov.cn |
| **国家医保局** | 推荐有账号 | 免费 | 医保身份查询；无需账号 | code.nhsa.gov.cn |
| **PubMed** | 推荐有账号 | 免费 | 临床文献检索；无需账号 | pubmed.ncbi.nlm.nih.gov |
| **万方数据** | 推荐有账号 | 免费账号 | 流行病学数据；主页可搜索，全文需账号 | wanfangdata.com.cn |
| **知网CNKI** | 推荐有账号 | 免费账号 | 临床文献；主页可搜索，全文需账号 | cnki.net |
| **中华医学会** | 推荐有账号 | 免费账号 | 临床指南/共识；主页可访问，部分指南需账号 | cma.org.cn |
| **小红书** | 可选 | 免费账号 | 消费者评价数据；探索页无需账号 | xiaohongshu.com |

> ⚠️ **开思CHIS账号是最关键缺口**。H模块（H01~H11）的市场概述数据完全依赖开思CHIS。无账号则该模块无法完成。

---

## 二、软件环境依赖

### 运行时环境

| 组件 | 版本要求 | 说明 |
|------|---------|------|
| **Python** | 3.10+ | 建议使用 3.12（bundled CPython in AI Shuo） |
| **OpenClaw** | 最新版 | AI Shuo内置，browser tool 依赖此运行 |
| **python-docx** | 最新版 | Word文档生成需要：`pip install python-docx` |

### 可选Python包

| 包名 | 用途 | 安装命令 |
|------|------|---------|
| `python-docx` | Markdown转Word报告 | `pip install python-docx` |
| `requests` | 轻量HTTP调用 | `pip install requests`（Python内置urllib可用时可省略）|
| `lxml` | XML/HTML解析（python-docx依赖）| 通常随python-docx自动安装 |

> AI Shuo Bundled Python已包含标准库（urllib等），无需额外安装requests。python-docx需手动安装。

---

## 三、网络环境依赖

- **必须可访问互联网**：所有数据源（药智网/开思CHIS/京东/PubMed等）均需公网访问
- **无代理要求**：目前未测试代理环境
- **防火墙**：确保 browser tool 的 profile="openclaw" 可正常打开目标URL

---

## 四、数据通道说明

> 详见 SKILL.md 中「数据通道验证状态」章节。以下为重点摘要：

| 平台 | 验证状态 | 关键URL | 备注 |
|------|---------|---------|------|
| 药智网 | ✅ 已验证 | db.yaozh.com | 部分数据需VIP |
| 开思CHIS | ✅ 已验证（需账号） | agent.sinohealth.com | SPA应用，需登录态 |
| 京东 | ✅ 已验证 | search.jd.com | 强制登录墙可能影响部分数据 |
| 天猫/淘宝 | ✅ 已验证 | ai.tmall.com | 有登录墙 |
| 美团 | ✅ 已验证（主页） | meituan.com | 医药子站数据有限 |
| NMPA | ✅ 已验证 | nmpa.gov.cn/datasearch | 无需登录 |
| 国家医保局 | ⚠️ 部分通过 | code.nhsa.gov.cn | JS未加载，部分数据以PDF为主 |
| PubMed | ✅ 已验证 | pubmed.ncbi.nlm.nih.gov | 全免费，无需账号 |
| 万方 | ✅ 已验证（主页） | wanfangdata.com.cn | 全文需账号 |
| 知网CNKI | ✅ 已验证（主页） | cnki.net | 有安全验证，全文需账号 |
| 中华医学会 | ✅ 已验证（主页） | cma.org.cn | 部分指南需账号 |
| 抖音创作平台 | ⚠️ 需登录 | creator.douyin.com | 需短信验证码 |
| 小红书 | ⚠️ 部分验证 | xiaohongshu.com | 探索页无需账号 |

---

## 五、账号准备检查清单

使用本Skill前，请确认以下账号已就绪：

```
【必选】
□ 开思CHIS VIP账号（若无，H模块无法完成）
□ 药智网账号（VIP更佳，免费账号可完成A/B/C/D/E/F/G基础数据）

【推荐】
□ 京东账号（jd_xxx）
□ 天猫/淘宝账号（tb_xxx）
□ 抖音账号（用于创作服务平台登录）

【可选】
□ 中华医学会账号
□ 万方/知网账号
□ 美团账号
```

---

## 六、第三方工具依赖

| 工具 | 来源 | 用途 |
|------|------|------|
| `session-manager.js` | 本Skill自带 | 登录态持久化管理，支持多平台Cookie保存 |
| `playwright-stealth.js` | 依赖playwright-scraper-skill | 反爬虫增强（可选，大部分场景不需要）|

> 注意：`session-manager.js` 和 `playwright-stealth.js` 均依赖 **Node.js** 环境。请确保 `node` 命令在 PATH 中可用。

---

## 七、快速安装脚本

在全新环境中，运行本Skill前请执行：

```bash
# 1. 安装Python依赖
pip install --user python-docx

# 2. 确认Node.js可用（session-manager.js需要）
node --version

# 3. 确认AI Shuo/OpenClaw可用
# （browser tool 依赖OpenClaw运行，AI Shuo内置）

# 4. 配置平台账号
# 参考上方「账号准备检查清单」，将账号信息填入 credentials.md
# （从 credentials-template.md 复制）
```

---

## 八、其他注意事项

1. **browser tool** 是本Skill的核心工具，依赖 OpenClaw 内置的浏览器实例（profile="openclaw"）
2. **web_fetch tool** 对国内医药类站点**几乎全部封锁**，请勿依赖它获取药智网/开思CHIS等数据
3. 开思CHIS 是 SPA 应用，直接通过 URL 访问子页面会404。需要通过主页搜索框触发搜索，然后通过点击结果进入各模块
4. 部分平台（京东/天猫）存在登录墙，建议在 browser tool 中提前登录并保持会话

---

*本文件版本：v1.0 | 更新日期：2026-04-23*
