# evaluation 脚本索引

## 脚本清单

| 脚本 | 用途 | 鉴权模式 |
|------|------|---------|
| `run_evaluation.py` | 按 3.1 版框架执行半自动评估编排 | access-token |
| `generate_report.py` | 汇总结论并生成 Markdown/Word 报告 | nologin |

---

## 鉴权前置条件

- `run_evaluation.py` 依赖各平台已登录会话，执行前先运行 `platform-auth/check_session.py`
- `generate_report.py` 无需鉴权，直接运行

---

## 运行方式

```bash
# 执行完整评估（所有阶段）
python scripts/evaluation/run_evaluation.py --product 门冬氨酸钙片

# 仅执行第一阶段
python scripts/evaluation/run_evaluation.py --product 阿司匹林 --stage 1

# 使用已采集数据执行评估
python scripts/evaluation/run_evaluation.py --product 阿司匹林 --data-dir .cms-log/data/阿司匹林

# 生成 Markdown 报告（输出到 stdout）
python scripts/evaluation/generate_report.py --result-file .cms-log/log/.../evaluation-xxx.json

# 生成 Word 报告
python scripts/evaluation/generate_report.py \
  --result-file .cms-log/log/.../evaluation-xxx.json \
  --format docx \
  --output 门冬氨酸钙片评估报告.docx
```

---

## 返回说明

`run_evaluation.py` 输出结构化 JSON，同时写入 `.cms-log/log/product-eval-data-acquisition/`：

```json
{
  "product": "门冬氨酸钙片",
  "evaluation_date": "2026-04-23",
  "framework_version": "3.1",
  "engine_mode": "semi-automatic",
  "final_verdict": "待人工复核",
  "terminated_by": null,
  "stage_results": {
    "stage_1": {
      "items": [
        {
          "rule": "A01",
          "name": "批文独家判断（Rx）",
          "applicable": null,
          "result": "待人工判读",
          "key_value": null,
          "evidence": null,
          "note": null,
          "missing_source": null
        }
      ],
      "total": 41,
      "passed": 0,
      "failed": 0,
      "manual_review": 39,
      "missing_data": 2
    }
  }
}
```

---

## 依赖

- `run_evaluation.py`：Python 标准库（无额外依赖）
- `generate_report.py`：
  - Markdown 格式：Python 标准库
  - Word 格式：`python-docx`（`pip install python-docx`）
- 第三阶段输出为人工评估占位项，不再返回空结果
