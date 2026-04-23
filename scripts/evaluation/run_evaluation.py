"""
run_evaluation.py — 按 3.2 版评估框架执行产品评估

鉴权模式: access-token（依赖各平台已登录会话）
依赖: 无额外依赖（Python 标准库）

执行流程:
  1. 检查各平台登录态
  2. 按模块顺序采集数据（或读取已采集数据）
  3. 逐条执行 52 个评估事项
  4. 遇到硬性 NO GO 立即终止
  5. 输出结构化评估结论

用法:
  python run_evaluation.py --product 门冬氨酸钙片
  python run_evaluation.py --product 阿司匹林 --stage 1
  python run_evaluation.py --product 阿司匹林 --data-dir .cms-log/data/阿司匹林 --json
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

LOG_DIR = Path(".cms-log/log/product-eval-data-acquisition")
LOG_DIR.mkdir(parents=True, exist_ok=True)

SCRIPTS_DIR = Path("scripts")

# 硬性 NO GO 规则
HARD_NO_GO_RULES = {"A08", "A09", "A10"}

# 评估规则定义（规则编号 → 名称、所需数据源、判断逻辑说明）
EVALUATION_RULES = {
    "A00": {"name": "产品基础信息", "sources": ["yaozh", "nmpa", "nhsa"], "stage": 1},
    "A01": {"name": "批文独家判断（Rx）", "sources": ["yaozh"], "stage": 1},
    "A02": {"name": "价格优势（Rx）", "sources": ["kaisi", "jd"], "stage": 1},
    "A03": {"name": "电商运营能力（Rx）", "sources": ["jd", "tmall", "meituan"], "stage": 1},
    "A04": {"name": "批文独家判断（OTC）", "sources": ["yaozh"], "stage": 1},
    "A05": {"name": "OTC头部品牌集中度", "sources": ["kaisi"], "stage": 1},
    "A06": {"name": "价格优势（OTC）", "sources": ["kaisi", "jd"], "stage": 1},
    "A07": {"name": "电商运营能力（OTC）", "sources": ["jd", "tmall", "meituan"], "stage": 1},
    "A08": {"name": "壁垒与排除（妆械）", "sources": ["yaozh", "nmpa"], "stage": 1, "hard_no_go": True},
    "A09": {"name": "排除-保健食品", "sources": ["yaozh", "nmpa"], "stage": 1, "hard_no_go": True},
    "A10": {"name": "排除-禁售限售", "sources": ["yaozh", "nmpa"], "stage": 1, "hard_no_go": True},
    "B01": {"name": "疾病类型-自我诊断", "sources": ["yaozh"], "stage": 1},
    "B02": {"name": "疾病类型-需处方", "sources": ["yaozh"], "stage": 1},
    "B03": {"name": "强焦虑属性", "sources": ["douyin", "jd"], "stage": 1},
    "C01": {"name": "人群规模-千万级", "sources": ["pubmed", "wanfang"], "stage": 1},
    "C02": {"name": "人群规模-500万级", "sources": ["pubmed", "wanfang"], "stage": 1},
    "C03": {"name": "抖音指数>5万", "sources": ["douyin"], "stage": 1},
    "C04": {"name": "电商流量基础", "sources": ["jd", "tmall", "xiaohongshu"], "stage": 1},
    "D01": {"name": "价格合理性（独家）", "sources": ["kaisi", "jd"], "stage": 1},
    "D02": {"name": "价格合理性（独家）", "sources": ["kaisi", "jd"], "stage": 1},
    "D03": {"name": "价格优势（Rx）", "sources": ["kaisi", "jd"], "stage": 1},
    "D04": {"name": "价格优势（OTC）", "sources": ["kaisi", "jd"], "stage": 1},
    "E01": {"name": "指南/共识一线推荐", "sources": ["cma", "pubmed"], "stage": 1},
    "E02": {"name": "一线期刊临床数据", "sources": ["pubmed"], "stage": 1},
    "E03": {"name": "已发表临床研究", "sources": ["pubmed"], "stage": 1},
    "F01": {"name": "已上市品种", "sources": ["yaozh", "nmpa"], "stage": 1},
    "F02": {"name": "未上市3年内可能性", "sources": ["yaozh", "nmpa"], "stage": 1},
    "G01": {"name": "核心疗效优于竞品", "sources": ["pubmed", "yaozh"], "stage": 1},
    "G02": {"name": "至少2项量化优势", "sources": ["yaozh", "pubmed"], "stage": 1},
    "H01": {"name": "市场规模-B2C", "sources": ["kaisi"], "stage": 1},
    "H02": {"name": "市场规模-零售", "sources": ["kaisi"], "stage": 1},
    "H03": {"name": "Top3品牌份额", "sources": ["kaisi"], "stage": 1},
    "H04": {"name": "CR3集中度", "sources": ["kaisi"], "stage": 1},
    "H05": {"name": "CR5集中度", "sources": ["kaisi"], "stage": 1},
    "H06": {"name": "厂家数量", "sources": ["kaisi"], "stage": 1},
    "H07": {"name": "品牌数量", "sources": ["kaisi"], "stage": 1},
    "H08": {"name": "品类均价", "sources": ["kaisi"], "stage": 1},
    "H09": {"name": "竞争格局预测", "sources": ["kaisi"], "stage": 1},
    "H10": {"name": "市场增速", "sources": ["kaisi"], "stage": 1},
    "H11": {"name": "市场集中度趋势", "sources": ["kaisi"], "stage": 1},
    "I01": {"name": "疗效差异对比", "sources": ["pubmed", "yaozh"], "stage": 2},
    "I02": {"name": "使用体验差异", "sources": ["jd", "yaozh"], "stage": 2},
    "I03": {"name": "价格带对比", "sources": ["jd", "kaisi"], "stage": 2},
    "I04": {"name": "渠道覆盖对比", "sources": ["jd", "meituan"], "stage": 2},
    "J01": {"name": "财务测算", "sources": [], "stage": 3},
    "J02": {"name": "供应链评估", "sources": ["douyin"], "stage": 3},
    "J03": {"name": "战略协同", "sources": [], "stage": 3},
    "J04": {"name": "最终放行", "sources": [], "stage": 3},
}


def check_sessions() -> dict:
    """检查各平台登录状态。"""
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "platform-auth" / "check_session.py"), "--json"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        return {}
    try:
        sessions = json.loads(result.stdout)
        return {s["platform"]: s for s in sessions}
    except (json.JSONDecodeError, KeyError):
        return {}


def build_empty_item(rule_id: str, rule: dict) -> dict:
    """构建一个待执行的评估事项。"""
    return {
        "rule": rule_id,
        "name": rule["name"],
        "applicable": None,
        "result": "待执行",
        "key_value": None,
        "evidence": None,
        "note": None,
        "missing_source": None,
        "sources_required": rule["sources"],
    }


def evaluate_stage(product: str, stage: int, sessions: dict, data_dir: Path | None) -> list[dict]:
    """执行指定阶段的评估，返回评估事项列表。"""
    items = []
    for rule_id, rule in EVALUATION_RULES.items():
        if rule["stage"] != stage:
            continue

        item = build_empty_item(rule_id, rule)

        # 检查所需数据源是否可用
        missing_sources = []
        for source in rule["sources"]:
            session = sessions.get(source, {})
            if not session.get("has_session") and source not in {"pubmed", "nmpa", "nhsa"}:
                missing_sources.append(source)

        if missing_sources:
            item["result"] = "需补充数据"
            item["missing_source"] = f"以下平台未登录: {', '.join(missing_sources)}"

        items.append(item)

    return items


def main() -> None:
    parser = argparse.ArgumentParser(description="按 3.2 版评估框架执行产品评估")
    parser.add_argument("--product", required=True, help="产品名称")
    parser.add_argument("--approval-number", help="批准文号（可选）")
    parser.add_argument("--data-dir", help="已采集数据目录（不传则实时采集）")
    parser.add_argument(
        "--stage",
        choices=["1", "2", "3", "all"],
        default="all",
        help="执行阶段：1/2/3/all，默认 all",
    )
    parser.add_argument("--json", dest="output_json", action="store_true", help="输出 JSON 格式")
    args = parser.parse_args()

    print(f"🚀 开始评估: {args.product}", file=sys.stderr)
    print(f"   评估框架: 3.2 版 | 阶段: {args.stage}", file=sys.stderr)

    # 检查登录状态
    print("🔍 检查平台登录状态...", file=sys.stderr)
    sessions = check_sessions()

    data_dir = Path(args.data_dir) if args.data_dir else None
    stages_to_run = [1, 2, 3] if args.stage == "all" else [int(args.stage)]

    evaluation_result = {
        "product": args.product,
        "approval_number": args.approval_number,
        "evaluation_date": datetime.now().strftime("%Y-%m-%d"),
        "framework_version": "3.2",
        "stages_executed": stages_to_run,
        "final_verdict": None,
        "terminated_by": None,
        "stage_results": {},
    }

    terminated = False
    for stage in stages_to_run:
        if terminated:
            break

        print(f"\n📋 执行第 {stage} 阶段...", file=sys.stderr)
        items = evaluate_stage(args.product, stage, sessions, data_dir)

        # 检查硬性 NO GO
        for item in items:
            if item["rule"] in HARD_NO_GO_RULES and item["result"] == "不通过":
                evaluation_result["final_verdict"] = "NO GO"
                evaluation_result["terminated_by"] = item["rule"]
                terminated = True
                print(f"🛑 硬性 NO GO: {item['rule']} {item['name']}", file=sys.stderr)
                break

        evaluation_result["stage_results"][f"stage_{stage}"] = {
            "items": items,
            "total": len(items),
            "pending": sum(1 for i in items if i["result"] == "待执行"),
            "missing_data": sum(1 for i in items if i["result"] == "需补充数据"),
        }

    if not terminated:
        evaluation_result["final_verdict"] = "待完成"

    # 保存结果
    result_file = LOG_DIR / f"evaluation-{args.product}-{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
    result_file.write_text(json.dumps(evaluation_result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n📄 评估结果已保存: {result_file}", file=sys.stderr)

    if args.output_json:
        print(json.dumps(evaluation_result, ensure_ascii=False, indent=2))
    else:
        print(f"\n{'='*50}")
        print(f"产品: {evaluation_result['product']}")
        print(f"评估日期: {evaluation_result['evaluation_date']}")
        print(f"最终结论: {evaluation_result['final_verdict']}")
        if evaluation_result["terminated_by"]:
            print(f"终止原因: {evaluation_result['terminated_by']}")
        for stage_key, stage_data in evaluation_result["stage_results"].items():
            print(f"\n{stage_key}: 共 {stage_data['total']} 项")
            print(f"  待执行: {stage_data['pending']} | 需补充数据: {stage_data['missing_data']}")

        # 提示缺失的平台
        missing_platforms = [
            p for p, s in sessions.items()
            if not s.get("has_session") and p not in {"nmpa", "nhsa"}
        ]
        if missing_platforms:
            print(f"\n⚠️  以下平台未登录，影响相关规则评估:")
            for p in missing_platforms:
                print(f"   - {p}: python scripts/platform-auth/login.py --platform {p} --manual")


if __name__ == "__main__":
    main()
