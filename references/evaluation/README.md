# evaluation — 产品评估执行

## 模块说明

按 3.2 版院外新产品筛选及评估框架，逐条执行 52 个评估事项，汇总 GO/NO GO 结论并生成结构化报告。

---

## 适用场景

- 对候选产品执行完整三阶段评估
- 对已采集数据进行规则判断
- 生成可交付的评估报告

---

## 评估框架结构

| 阶段 | 模块 | 事项数 | 说明 |
|------|------|--------|------|
| 第一阶段 | A-H | 约 40 项 | 入门筛选（批文/价格/市场/学术） |
| 第二阶段 | I | 约 8 项 | 深度产品维度（竞品对比） |
| 第三阶段 | J | 约 4 项 | 最终放行（财务/供应链/战略） |

---

## 硬性 NO GO 规则（任一触发即终止）

| 规则 | 触发条件 |
|------|---------|
| A08 | 产品属于妆字号或器械，无药品壁垒 |
| A09 | 批准文号为保健食品（国食健字/卫食健字/国妆特字） |
| A10 | 产品属于禁售或限售品类 |

---

## 动作列表

### run_evaluation — 执行完整评估

**鉴权模式**: `access-token`

**输入**:

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| `--product` | string | 是 | 产品名称 |
| `--approval-number` | string | 否 | 批准文号 |
| `--data-dir` | string | 否 | 已采集数据目录，不传则实时采集 |
| `--stage` | string | 否 | 执行阶段：`1`/`2`/`3`/`all`，默认 `all` |

**输出**:

```json
{
  "product": "门冬氨酸钙片",
  "evaluation_date": "2026-04-23",
  "stage_1": {
    "verdict": "GO",
    "items": [
      {
        "rule": "A01",
        "name": "批文独家判断",
        "applicable": true,
        "result": "通过",
        "key_value": "同API批文=1家，独家窗口≈5年",
        "evidence": "药智网，API检索，2026-04-23",
        "note": "独家依据充分",
        "missing_source": null
      }
    ]
  },
  "final_verdict": "GO"
}
```

---

### generate_report — 生成评估报告

**鉴权模式**: `nologin`

**输入**:

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| `--result-file` | string | 是 | `run_evaluation.py` 输出的 JSON 文件路径 |
| `--format` | string | 否 | `markdown`（默认）或 `docx` |
| `--output` | string | 否 | 输出文件路径，默认输出到 stdout |

**输出**: Markdown 或 Word 格式的完整评估报告

---

## 输出字段规范

每条评估事项的输出必须包含以下字段：

| 字段 | 说明 | 示例 |
|------|------|------|
| `rule` | 规则编号 | `A01` |
| `name` | 规则名称 | `批文独家判断` |
| `applicable` | 是否适用 | `true` / `false` |
| `result` | 判断结论 | `通过` / `不通过` / `需补充数据` |
| `key_value` | 关键数值 | `同API批文=1家` |
| `evidence` | 数据来源 | `药智网，2026-04-23` |
| `note` | 判断说明 | `独家依据充分` |
| `missing_source` | 缺失数据来源 | `null` 或说明 |

---

## 约束

- 遇到硬性 NO GO 规则触发时，立即停止并输出终止原因，不继续后续评估
- 数据缺口（`missing_source` 非 null）不阻断评估，但必须在报告中标注
- `generate_report.py` 生成 docx 格式时依赖 `python-docx`（`pip install python-docx`）
