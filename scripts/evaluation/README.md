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

# 执行评估但不主动拉起登录引导
python scripts/evaluation/run_evaluation.py --product 门冬氨酸钙片 --no-auto-login

# 执行评估但不自动补采数据
python scripts/evaluation/run_evaluation.py --product 门冬氨酸钙片 --no-auto-fetch

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

当 `run_evaluation.py` 发现当前阶段所需平台既没有现成数据文件、也没有有效登录态时：

- 交互式终端下会主动逐个平台弹出手动登录引导
- 用户完成浏览器中的扫码/短信/账号登录后，流程继续执行
- 传入 `--no-auto-login` 或 `--json` 时，不弹出浏览器，仅报告缺口

当登录态可用但数据文件仍缺失时：

- 会自动调用可直接基于产品名执行的采集脚本补采
- 当前支持自动补采的来源包括：药智网、NMPA、国家医保局、开思、京东/天猫/美团/饿了么、抖音、小红书、PubMed/万方/知网、丁香园
- 医生资源、指南等仍需更明确的疾病/科室上下文，当前不会自动补采
- 传入 `--no-auto-fetch` 或 `--json` 时，不执行自动补采

---

## 依赖

- `run_evaluation.py`：Python 标准库（无额外依赖）
- `generate_report.py`：
  - Markdown 格式：Python 标准库
  - Word 格式：`python-docx`（`pip install python-docx`）
- 第三阶段输出为人工评估占位项，不再返回空结果
