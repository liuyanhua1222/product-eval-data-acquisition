---
name: product-eval-data-acquisition
description: 执行院外新产品三阶段筛选评估，自动采集多平台数据并输出 GO/NO GO 结论
skillcode: product-eval-data-acquisition
github: https://github.com/xgjk/xg-skills/tree/main/product-eval-data-acquisition
dependencies:
  - cms-auth-skills
---

# product-eval-data-acquisition — 索引

本文件提供能力边界、路由规则与使用约束。详细说明见 `references/`，实际执行见 `scripts/`。

**当前版本**: 4.0.0
**接口版本**: v1

---

## 能力概览（3 块能力）

- `platform-auth`：管理各数据平台的登录态与 Cookie 会话
- `data-acquisition`：使用已登录会话从各平台采集评估所需数据
- `evaluation`：按 3.2 版评估框架逐条执行 52 个评估事项，输出结构化报告

---

## 统一规范

- 鉴权依赖：`cms-auth-skills/SKILL.md`
- 运行日志：`.cms-log/log/product-eval-data-acquisition/`
- 会话状态：`~/.agent-browser/sessions/<platform>-cookies.json`
- 输出格式：所有脚本默认输出结构化 JSON

---

## 授权依赖

- 需要鉴权时先读取 `cms-auth-skills/SKILL.md`
- 依赖缺失时先安装依赖，再继续执行

---

## 输入完整性规则

执行评估前，以下输入必须齐全，否则停止并提示用户补充：

| 输入项 | 必须/可选 | 说明 |
|--------|---------|------|
| 产品名称 | 必须 | 中文通用名，如"门冬氨酸钙片" |
| 批准文号 | 可选 | 有则优先用，无则通过产品名查询 |
| 开思CHIS 账号 | 必须（H 模块） | 无账号则 H01-H11 全部无法完成 |
| 药智网账号 | 推荐 | VIP 账号可解锁电商销售数据 |
| 抖音账号 | 推荐 | 无账号则 C03/B03 无法完成 |

---

## 建议工作流

1. 读取本 `SKILL.md`，确认能力边界和限制
2. 执行 `platform-auth/check_session.py` 确认各平台登录态
3. 对缺失登录态的平台执行 `platform-auth/login.py`
4. 按评估模块顺序执行 `data-acquisition/` 下对应脚本采集数据
5. 执行 `evaluation/run_evaluation.py` 汇总评估结论
6. 输出最终报告

---

## 脚本使用规则

- 所有脚本均可在命令行独立运行
- 执行前确认对应平台已登录（`check_session.py` 验证）
- 对用户有副作用的操作（登录、写入文件）执行前再次确认
- 日志和状态文件统一写入 `.cms-log/`，不写回 Skill 包目录

---

## 路由与加载规则

- 按用户意图定位模块，读取对应 `references/<module>/README.md`
- 补齐必要输入后执行对应脚本
- 脚本路径以本文件路由表为准

---

## 宪章

- 本 Skill 不自行实现登录流程，鉴权统一依赖 `cms-auth-skills`
- 凭证信息不存储在 Skill 包目录内
- 危险操作（批量写入、清除会话）执行前必须确认

---

## 模块路由表

| 用户意图 | 模块 | 能力摘要 | 模块说明 | 脚本 |
|---------|------|---------|---------|------|
| 查看各平台登录状态 | `platform-auth` | 检查所有平台 Cookie 是否有效 | `./references/platform-auth/README.md` | `./scripts/platform-auth/check_session.py` |
| 登录某个平台 | `platform-auth` | 自动化填表或手动登录并保存 Cookie | `./references/platform-auth/README.md` | `./scripts/platform-auth/login.py` |
| 清除某平台会话 | `platform-auth` | 删除指定平台的 Cookie 文件 | `./references/platform-auth/README.md` | `./scripts/platform-auth/clear_session.py` |
| 采集药智网批文数据 | `data-acquisition` | 查询批准文号、企业、剂型、医保类别 | `./references/data-acquisition/README.md` | `./scripts/data-acquisition/fetch_yaozh.py` |
| 采集开思CHIS市场数据 | `data-acquisition` | 查询市场规模、品牌份额、Top3 | `./references/data-acquisition/README.md` | `./scripts/data-acquisition/fetch_kaisi.py` |
| 采集电商平台数据 | `data-acquisition` | 查询京东/天猫价格、销量、评价 | `./references/data-acquisition/README.md` | `./scripts/data-acquisition/fetch_ecommerce.py` |
| 采集抖音关键词指数 | `data-acquisition` | 查询抖音指数（搜索指数/综合指数） | `./references/data-acquisition/README.md` | `./scripts/data-acquisition/fetch_douyin.py` |
| 采集学术文献数据 | `data-acquisition` | 查询 PubMed/万方/知网临床文献 | `./references/data-acquisition/README.md` | `./scripts/data-acquisition/fetch_literature.py` |
| 执行完整产品评估 | `evaluation` | 按框架 3.2 执行 52 个评估事项 | `./references/evaluation/README.md` | `./scripts/evaluation/run_evaluation.py` |
| 生成评估报告 | `evaluation` | 汇总结论并输出结构化报告 | `./references/evaluation/README.md` | `./scripts/evaluation/generate_report.py` |

---

## 能力树

```
product-eval-data-acquisition/
├── SKILL.md
├── references/
│   ├── platform-auth/
│   │   └── README.md
│   ├── data-acquisition/
│   │   └── README.md
│   └── evaluation/
│       └── README.md
└── scripts/
    ├── platform-auth/
    │   ├── README.md
    │   ├── check_session.py
    │   ├── login.py
    │   └── clear_session.py
    ├── data-acquisition/
    │   ├── README.md
    │   ├── fetch_yaozh.py
    │   ├── fetch_kaisi.py
    │   ├── fetch_ecommerce.py
    │   ├── fetch_douyin.py
    │   └── fetch_literature.py
    └── evaluation/
        ├── README.md
        ├── run_evaluation.py
        └── generate_report.py
```
