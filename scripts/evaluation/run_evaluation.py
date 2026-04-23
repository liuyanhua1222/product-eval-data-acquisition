"""
run_evaluation.py — 按 3.1 版评估框架执行产品评估编排

鉴权模式: access-token（依赖各平台已登录会话）
依赖: 无额外依赖（Python 标准库）

执行流程:
  1. 检查各平台登录态
  2. 读取已采集数据或给出缺口提示
  3. 对可自动判定的规则执行基础判断
  4. 对需人工解读的规则输出待人工判读状态
  5. 输出结构化评估编排结果
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

LOG_DIR = Path(".cms-log/log/product-eval-data-acquisition")
LOG_DIR.mkdir(parents=True, exist_ok=True)

SCRIPTS_DIR = Path("scripts")
PUBLIC_SOURCES = {"pubmed", "nmpa", "nhsa"}
MANUAL_RESULT = "待人工判读"
NEEDS_DATA_RESULT = "需补充数据"
LOGIN_PLATFORM_ORDER = [
    "yaozh",
    "kaisi",
    "douyin",
    "xiaohongshu",
    "jd",
    "tmall",
    "meituan",
    "eleme",
    "wanfang",
    "cnki",
    "cma",
]
SOURCE_TO_LOGIN_PLATFORM = {
    "doctor": "douyin",
}
FETCHABLE_SOURCES = {
    "yaozh",
    "nmpa",
    "nhsa",
    "kaisi",
    "jd",
    "tmall",
    "meituan",
    "eleme",
    "douyin",
    "xiaohongshu",
    "pubmed",
    "wanfang",
    "cnki",
    "dingxiangyuan",
}

SOURCE_FILE_PREFIXES = {
    "yaozh": "yaozh-",
    "nmpa": "nmpa-",
    "nhsa": "nhsa-",
    "kaisi": "kaisi-",
    "jd": "jd-",
    "tmall": "tmall-",
    "meituan": "meituan-",
    "eleme": "eleme-",
    "jddaojia": "jddaojia-",
    "douyin": "douyin-",
    "juliang": "juliang-",
    "xiaohongshu": "xiaohongshu-",
    "pubmed": "pubmed-",
    "wanfang": "wanfang-",
    "cnki": "cnki-",
    "dingxiangyuan": "dxy-",
    "guideline": "guideline-",
    "doctor": "doctor-",
}

STAGE_3_MANUAL_RULES = {
    "L01": {
        "name": "盈利能力评估",
        "sources": [],
        "stage": 3,
        "missing_source_default": "需补充财务测算、毛利率、费用率、回本周期等内部数据",
        "manual_only": True,
        "note": "第三阶段为人工评估项，本脚本仅保留占位并提示补充内部数据",
    },
    "M01": {
        "name": "供应链与产能评估",
        "sources": [],
        "stage": 3,
        "missing_source_default": "需补充厂家产能、原料稳定性、扩产计划等内部数据",
        "manual_only": True,
        "note": "第三阶段为人工评估项，本脚本仅保留占位并提示补充内部数据",
    },
    "N01": {
        "name": "战略协同评估",
        "sources": [],
        "stage": 3,
        "missing_source_default": "需补充内部品类策略、渠道协同、组织资源等信息",
        "manual_only": True,
        "note": "第三阶段为人工评估项，本脚本仅保留占位并提示补充内部数据",
    },
}

# 硬性 NO GO 规则（任一触发即终止）
HARD_NO_GO_RULES = {"A09", "A10"}

# 评估规则定义（对齐 3.1 版标准文档 A00-K02）
EVALUATION_RULES = {
    "A00": {"name": "产品基础信息", "sources": ["yaozh", "nmpa", "nhsa"], "stage": 1, "note": "输出批准文号、企业名称、剂型、规格、适应症、批准日期、医保类别"},
    "A01": {"name": "Rx 独家批文及独家周期", "sources": ["yaozh", "nmpa"], "stage": 1, "condition": "Rx 产品", "pass_rule": "同 API 同剂型仅本企业有效批文，独家周期 ≥ 3 年"},
    "A02": {"name": "Rx 非独家价格优势", "sources": ["kaisi", "jd", "tmall"], "stage": 1, "condition": "Rx 非独家", "pass_rule": "本品零售价比同 API Top1 低 ≥ 25%"},
    "A03": {"name": "Rx 非独家无价格优势时竞品电商运营能力", "sources": ["jd", "tmall", "meituan"], "stage": 1, "condition": "Rx 非独家且价差 < 25%", "pass_rule": "竞品 B2C 或 O2O 满足弱运营任一项"},
    "A04": {"name": "OTC 独家批文及独家周期", "sources": ["yaozh", "nmpa"], "stage": 1, "condition": "OTC 产品", "pass_rule": "同 API 同剂型同适应症仅本企业有效批文，独家周期 ≥ 3 年"},
    "A05": {"name": "OTC 非独家头部品牌集中度", "sources": ["kaisi"], "stage": 1, "condition": "OTC 非独家", "pass_rule": "同 API Top1 品牌市占率 < 50%"},
    "A06": {"name": "OTC 非独家且头部强势时价格优势", "sources": ["kaisi", "jd", "tmall"], "stage": 1, "condition": "OTC 非独家且 Top1 ≥ 50%", "pass_rule": "本品零售价比 Top1 低 ≥ 25%"},
    "A07": {"name": "OTC 非独家无价格优势时头部品牌电商运营能力", "sources": ["jd", "tmall", "meituan"], "stage": 1, "condition": "OTC 非独家且价差 < 25%", "pass_rule": "头部品牌 B2C 或 O2O 满足弱运营任一项"},
    "A08": {"name": "妆字号/器械竞争壁垒", "sources": ["yaozh", "nmpa"], "stage": 1, "condition": "妆字号或器械产品", "pass_rule": "存在独家成分/专利/剂型/学术/生产/原料壁垒任一项"},
    "A09": {"name": "保健食品/功能性食品/跨境产品排除", "sources": ["yaozh", "nmpa"], "stage": 1, "hard_no_go": True, "pass_rule": "不属于保健食品/功能性食品/跨境产品则通过"},
    "A10": {"name": "线上药店禁售/限售排除", "sources": ["yaozh", "nmpa"], "stage": 1, "hard_no_go": True, "pass_rule": "不属于禁售/限售品类则通过"},
    "B01": {"name": "疾病可自我诊断和自我用药", "sources": ["yaozh"], "stage": 1, "pass_rule": "无需医生诊断/检测，患者可自主判断并用药"},
    "B02": {"name": "疾病需医生诊断但患者可自我选择用药", "sources": ["yaozh"], "stage": 1, "pass_rule": "确诊依赖医生，但患者有自购/线上购药空间"},
    "B03": {"name": "强焦虑疾病/需求属性", "sources": ["douyin", "jd", "tmall"], "stage": 1, "pass_rule": "属于外貌/健康/形象/生活/隐私焦虑任一类"},
    "B04": {"name": "高频反复或长周期需求", "sources": ["yaozh"], "stage": 1, "pass_rule": "具有高频、反复、长周期或周期性用药特征"},
    "C01": {"name": "国内患者或需求人群千万级", "sources": ["pubmed", "wanfang", "cnki"], "stage": 1, "pass_rule": "权威流行病学支持国内人群 ≥ 1000 万"},
    "C02": {"name": "国内需就诊/用药人群 500 万级", "sources": ["pubmed", "wanfang", "cnki"], "stage": 1, "pass_rule": "需就诊或用药人群 ≥ 500 万"},
    "C03": {"name": "抖音站内搜索指数 > 5 万", "sources": ["douyin"], "stage": 1, "pass_rule": "相关核心词抖音搜索指数 > 50000"},
    "C04": {"name": "京东/阿里/美团补充流量基础", "sources": ["jd", "tmall", "meituan"], "stage": 1, "condition": "C03 不通过时", "pass_rule": "三大平台任一有明确搜索热度/销量/购买人群证据"},
    "D01": {"name": "独家且有差异/创新产品定价合理性", "sources": ["kaisi", "jd", "tmall"], "stage": 1, "condition": "独家且有差异或创新", "pass_rule": "本品价格 ≤ 同品类均价 × 1.5"},
    "D02": {"name": "独家但无显著差异产品定价合理性", "sources": ["kaisi", "jd", "tmall"], "stage": 1, "condition": "独家且无显著差异", "pass_rule": "本品价格与市场 Top3 主流价格区间相当"},
    "D03": {"name": "Rx 非独家产品低价优势", "sources": ["kaisi", "jd", "tmall"], "stage": 1, "condition": "Rx 非独家", "pass_rule": "本品零售价比头部品牌低 ≥ 25%"},
    "D04": {"name": "OTC 非独家产品低价优势", "sources": ["kaisi", "jd", "tmall"], "stage": 1, "condition": "OTC 非独家", "pass_rule": "本品零售价比头部品牌低 15%-20% 或以上"},
    "E01": {"name": "指南/专家共识一线推荐", "sources": ["pubmed"], "stage": 1, "pass_rule": "被指南或专家共识推荐为一线或核心治疗选择"},
    "E02": {"name": "非一线推荐但有一线期刊临床数据", "sources": ["pubmed", "wanfang", "cnki"], "stage": 1, "condition": "E01 不通过", "pass_rule": "在一线期刊发表过相关临床研究数据"},
    "E03": {"name": "已发表相关临床研究论文", "sources": ["pubmed", "wanfang", "cnki"], "stage": 1, "condition": "E01/E02 不通过", "pass_rule": "已发表与目标适应症相关的临床研究论文"},
    "F01": {"name": "已上市品种判断", "sources": ["yaozh", "nmpa"], "stage": 1, "pass_rule": "存在有效批准文号且状态支持上市销售"},
    "F02": {"name": "未上市产品 3 年内上市可能性", "sources": ["yaozh", "nmpa"], "stage": 1, "condition": "F01 不通过", "pass_rule": "根据注册/审评/临床进度可合理判断 3 年内上市"},
    "G01": {"name": "核心疗效优于主流竞品", "sources": ["pubmed", "wanfang", "cnki"], "stage": 1, "pass_rule": "临床或真实世界数据证明核心疗效指标明确优于竞品"},
    "G02": {"name": "无核心疗效优势时至少 2 项量化优势", "sources": ["yaozh", "pubmed"], "stage": 1, "condition": "G01 不通过", "pass_rule": "起效更快/疗效更稳定/安全性更优/适用人群更广，至少 2 项"},
    "H01": {"name": "独家品种同适应症/同品类市场规模", "sources": ["kaisi"], "stage": 1, "condition": "独家品种", "note": "输出近三年 B2C 规模、线下药店规模、同比、渠道占比"},
    "H02": {"name": "独家品种同适应症/同品类价格和转化", "sources": ["kaisi", "jd", "tmall"], "stage": 1, "condition": "独家品种", "note": "输出盒单价、日服用成本、行业平均转换率、平均客单价"},
    "H03": {"name": "独家品种 Top3 竞品市场表现", "sources": ["kaisi", "jd", "tmall"], "stage": 1, "condition": "独家品种", "note": "输出 Top3 近三年规模、份额、同比、客单价、日服用价格"},
    "H04": {"name": "非独家品种同适应症/同品类整体规模", "sources": ["kaisi"], "stage": 1, "condition": "非独家品种", "note": "输出近三年 B2C 规模、线下药店规模、同比、渠道占比"},
    "H05": {"name": "非独家品种同 API 市场格局", "sources": ["kaisi", "nmpa", "yaozh"], "stage": 1, "condition": "非独家品种", "note": "输出同 API 近三年规模、份额、上市产品数、市场集中度"},
    "H06": {"name": "非独家品种同 API 价格和转化", "sources": ["kaisi", "jd", "tmall"], "stage": 1, "condition": "非独家品种", "note": "输出同 API 盒单价、日服用成本、行业平均转换率、平均客单价"},
    "H07": {"name": "非独家品种同 API Top3 市场表现", "sources": ["kaisi"], "stage": 1, "condition": "非独家品种", "note": "输出同 API Top3 近三年规模、份额、同比"},
    "H08": {"name": "非独家品种同 API Top3 价格表现", "sources": ["kaisi", "jd", "tmall"], "stage": 1, "condition": "非独家品种", "note": "输出同 API Top3 盒单价、日服用成本、平均客单价"},
    "H09": {"name": "竞争格局 3-5 年变化预测", "sources": ["nmpa", "yaozh"], "stage": 1, "note": "输出已上市/在研/临床企业数，判断 3-5 年竞争格局"},
    "H10": {"name": "市场进入壁垒", "sources": ["nmpa", "kaisi", "pubmed"], "stage": 1, "note": "输出专利/技术/品牌/生产/学术/渠道壁垒类型和强度"},
    "H11": {"name": "同 API 强势品牌和新进入者威胁", "sources": ["kaisi", "nmpa", "jd"], "stage": 1, "condition": "非独家品种", "note": "输出强势品牌压力和新进入威胁程度"},
    "I01": {"name": "本品与竞品疗效差异", "sources": ["pubmed", "wanfang", "cnki"], "stage": 2, "note": "输出各竞品疗效终点对比差异"},
    "I02": {"name": "本品与竞品非疗效差异", "sources": ["yaozh", "pubmed"], "stage": 2, "note": "输出起效时间/安全性/副作用/作用周期/适用人群对比"},
    "I03": {"name": "本品与竞品使用体验差异", "sources": ["yaozh", "jd", "tmall"], "stage": 2, "note": "输出便捷性/身体体感/依从性三维度对比"},
    "I04": {"name": "独家品种价格带和 Top3 对比", "sources": ["kaisi", "jd", "tmall"], "stage": 2, "condition": "独家品种", "note": "输出品类主流价格区间、本品与 Top3 价格对比"},
    "I05": {"name": "非独家品种同 API 价格带和 Top3 对比", "sources": ["kaisi", "jd", "tmall"], "stage": 2, "condition": "非独家品种", "note": "输出同 API 主流价格区间、本品与 Top3 价格对比"},
    "I06": {"name": "指南/共识学术地位相对竞品", "sources": ["pubmed"], "stage": 2, "note": "输出本品在指南/共识中推荐顺位相较竞品的位置"},
    "I07": {"name": "非指南/共识推荐时的临床治疗选择位置", "sources": ["pubmed", "wanfang", "cnki"], "stage": 2, "condition": "I06 不适用", "note": "输出本品在临床治疗路径中的位置（主流/补充/替代/后线）"},
    "J01": {"name": "人群规模趋势", "sources": ["pubmed", "wanfang", "cnki"], "stage": 2, "note": "输出患病率及就诊/需求人群近三年增长趋势和 CAGR"},
    "J02": {"name": "抖音/小红书搜索趋势", "sources": ["douyin", "xiaohongshu"], "stage": 2, "note": "输出近三年站内搜索人群或关键词指数同比和 CAGR"},
    "K01": {"name": "可合作医生数量和粉丝规模", "sources": ["doctor"], "stage": 2, "note": "输出抖音/视频号可合作医生数量、垂直科室医生数量、粉丝总量"},
    "K02": {"name": "产品与现有新媒体医生库匹配度", "sources": [], "stage": 2, "note": "输出可直接合作/需拓展/空白三类匹配结论（需内部医生库）", "missing_source_default": "需补充内部新媒体医生库", "manual_only": True},
}

EVALUATION_RULES.update(STAGE_3_MANUAL_RULES)


def check_sessions() -> dict:
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
    return {
        "rule": rule_id,
        "name": rule["name"],
        "applicable": None,
        "result": MANUAL_RESULT if rule.get("manual_only") else "待采集或判读",
        "key_value": None,
        "evidence": None,
        "note": rule.get("note") or rule.get("pass_rule"),
        "missing_source": rule.get("missing_source_default"),
        "sources_required": rule["sources"],
        "condition": rule.get("condition"),
    }


def flatten_text(value) -> str:
    if isinstance(value, dict):
        return " ".join(flatten_text(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(flatten_text(v) for v in value)
    return str(value or "")


def collect_data_files(data_dir: Path | None, product: str) -> dict[str, list[Path]]:
    base_dir = data_dir or LOG_DIR
    if not base_dir.exists():
        return {}

    files_by_source: dict[str, list[Path]] = {}
    for source, prefix in SOURCE_FILE_PREFIXES.items():
        candidates = sorted(base_dir.glob(f"{prefix}*.json"))
        if data_dir is None:
            if product:
                candidates = [p for p in candidates if product in p.name]
        elif product:
            product_candidates = [p for p in candidates if product in p.name]
            if product_candidates:
                candidates = product_candidates
        if candidates:
            files_by_source[source] = candidates
    return files_by_source


def collect_missing_login_platforms(stages_to_run: list[int], files_by_source: dict[str, list[Path]]) -> list[str]:
    required_platforms = set()
    for rule in EVALUATION_RULES.values():
        if rule["stage"] not in stages_to_run:
            continue
        for source in rule["sources"]:
            if source in PUBLIC_SOURCES or source in files_by_source:
                continue
            platform = SOURCE_TO_LOGIN_PLATFORM.get(source, source)
            if platform not in PUBLIC_SOURCES:
                required_platforms.add(platform)

    return [platform for platform in LOGIN_PLATFORM_ORDER if platform in required_platforms]


def collect_missing_sources(stages_to_run: list[int], files_by_source: dict[str, list[Path]]) -> list[str]:
    required_sources = set()
    for rule in EVALUATION_RULES.values():
        if rule["stage"] not in stages_to_run:
            continue
        for source in rule["sources"]:
            if source in files_by_source:
                continue
            required_sources.add(source)
    ordered = [source for source in SOURCE_FILE_PREFIXES if source in required_sources]
    extras = [source for source in required_sources if source not in SOURCE_FILE_PREFIXES]
    return ordered + sorted(extras)


def ensure_sessions_for_platforms(platforms: list[str], sessions: dict, output_json: bool) -> dict:
    if not platforms or output_json or not sys.stdin.isatty():
        return sessions

    print("\n🔐 检测到后续评估缺少登录态，开始进入引导式登录流程...", file=sys.stderr)
    print("   我会按需逐个平台打开登录页；你在弹出的浏览器中完成登录后，流程会继续。", file=sys.stderr)

    for platform in platforms:
        if sessions.get(platform, {}).get("has_session"):
            continue

        print(f"\n➡️  准备登录平台: {platform}", file=sys.stderr)
        confirm = input(f"现在打开 {platform} 的登录窗口吗？(Y/n) ").strip().lower()
        if confirm == "n":
            print(f"⏭️  已跳过 {platform}，相关规则后续会标记为需补充数据。", file=sys.stderr)
            continue

        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "platform-auth" / "login.py"), "--platform", platform, "--manual"],
            text=True,
        )
        if result.returncode != 0:
            print(f"⚠️  {platform} 登录流程未完成或执行失败，相关规则将继续标记为需补充数据。", file=sys.stderr)

        sessions = check_sessions()

    return sessions


def build_fetch_command(source: str, product: str, approval_number: str | None) -> list[str] | None:
    base = [sys.executable]
    if source == "yaozh":
        cmd = [str(SCRIPTS_DIR / "data-acquisition" / "fetch_yaozh.py"), "--product", product]
        if approval_number:
            cmd.extend(["--approval-number", approval_number])
        return base + cmd
    if source == "nmpa":
        cmd = [str(SCRIPTS_DIR / "data-acquisition" / "fetch_nmpa.py")]
        if approval_number:
            cmd.extend(["--approval-number", approval_number])
        else:
            cmd.extend(["--product", product])
        return base + cmd
    if source == "nhsa":
        return base + [str(SCRIPTS_DIR / "data-acquisition" / "fetch_nhsa.py"), "--product", product]
    if source == "kaisi":
        return base + [str(SCRIPTS_DIR / "data-acquisition" / "fetch_kaisi.py"), "--product", product]
    if source in {"jd", "tmall", "meituan", "eleme"}:
        return base + [
            str(SCRIPTS_DIR / "data-acquisition" / "fetch_ecommerce.py"),
            "--product",
            product,
            "--platform",
            source,
        ]
    if source == "douyin":
        return base + [str(SCRIPTS_DIR / "data-acquisition" / "fetch_douyin.py"), "--keywords", product]
    if source == "xiaohongshu":
        return base + [str(SCRIPTS_DIR / "data-acquisition" / "fetch_xiaohongshu.py"), "--keywords", product]
    if source in {"pubmed", "wanfang", "cnki"}:
        # 文献类来源不自动补采，因为需要根据具体规则确定检索词（疾病/适应症/API/产品名）
        return None
    if source == "dingxiangyuan":
        return base + [str(SCRIPTS_DIR / "data-acquisition" / "fetch_dingxiangyuan.py"), "--product", product]
    return None


def auto_fetch_missing_sources(
    stages_to_run: list[int],
    files_by_source: dict[str, list[Path]],
    sessions: dict,
    product: str,
    approval_number: str | None,
    interactive_enabled: bool,
) -> None:
    if not interactive_enabled:
        return

    missing_sources = collect_missing_sources(stages_to_run, files_by_source)
    fetch_targets = [source for source in missing_sources if source in FETCHABLE_SOURCES]
    if not fetch_targets:
        return

    print("\n📦 检测到部分数据源尚未采集，开始自动补采可执行的数据源...", file=sys.stderr)
    for source in fetch_targets:
        platform = SOURCE_TO_LOGIN_PLATFORM.get(source, source)
        if source not in PUBLIC_SOURCES and not sessions.get(platform, {}).get("has_session"):
            continue

        cmd = build_fetch_command(source, product, approval_number)
        if not cmd:
            continue

        print(f"   ▶ 自动采集 {source} ...", file=sys.stderr)
        result = subprocess.run(cmd, text=True)
        if result.returncode != 0:
            print(f"   ⚠️  {source} 自动采集失败，后续继续保留缺口提示。", file=sys.stderr)


def load_source_payloads(files_by_source: dict[str, list[Path]]) -> dict[str, list[dict]]:
    payloads: dict[str, list[dict]] = {}
    for source, files in files_by_source.items():
        for path in files:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            payloads.setdefault(source, []).append(data)
    return payloads


def latest_evidence(files_by_source: dict[str, list[Path]], source: str) -> str | None:
    files = files_by_source.get(source, [])
    if not files:
        return None
    return str(files[-1])


def find_matches(text: str, keywords: list[str]) -> list[str]:
    lowered = text.lower()
    return [kw for kw in keywords if kw.lower() in lowered]


def evaluate_rule(rule_id: str, item: dict, rule: dict, files_by_source: dict[str, list[Path]], payloads: dict[str, list[dict]]) -> dict:
    required_sources = rule["sources"]
    missing_sources = [source for source in required_sources if source not in files_by_source]
    missing_public_sources = [
        source for source in missing_sources
        if source in PUBLIC_SOURCES and not latest_evidence(files_by_source, source)
    ]
    missing_logged_sources = [source for source in missing_sources if source not in PUBLIC_SOURCES]
    all_missing = missing_logged_sources + missing_public_sources

    if rule.get("manual_only"):
        item["result"] = MANUAL_RESULT
        item["missing_source"] = rule.get("missing_source_default")
        return item

    if all_missing:
        item["result"] = NEEDS_DATA_RESULT
        item["missing_source"] = f"缺少数据文件: {', '.join(all_missing)}"
        return item

    evidence_paths = [latest_evidence(files_by_source, source) for source in required_sources]
    evidence_paths = [path for path in evidence_paths if path]
    item["evidence"] = " | ".join(evidence_paths) if evidence_paths else None

    text_blob = " ".join(flatten_text(payload) for source in required_sources for payload in payloads.get(source, []))

    if rule_id == "A09":
        hits = find_matches(text_blob, ["保健食品", "功能性食品", "跨境"])
        if hits:
            item["result"] = "不通过"
            item["key_value"] = ",".join(hits)
            item["note"] = "命中硬性排除关键词"
        else:
            item["result"] = "通过"
            item["note"] = "已完成基础关键词排查，未命中硬性排除词"
        return item

    if rule_id == "A10":
        hits = find_matches(text_blob, ["禁售", "限售", "疫苗", "血液制品", "麻醉药品", "精神药品"])
        if hits:
            item["result"] = "不通过"
            item["key_value"] = ",".join(hits)
            item["note"] = "命中线上禁售/限售相关关键词"
        else:
            item["result"] = "通过"
            item["note"] = "已完成基础关键词排查，未命中线上禁售/限售词"
        return item

    if rule_id == "F01":
        records = []
        for payload in payloads.get("yaozh", []):
            if isinstance(payload, dict):
                records.extend(payload.get("records", []))
        if records:
            item["result"] = "通过"
            item["key_value"] = f"药智网记录数={len(records)}"
            item["note"] = "检测到已采集批文记录，可视为已上市基础证据"
        else:
            item["result"] = MANUAL_RESULT
            item["note"] = "已有数据文件，但未解析出结构化批文记录，需人工判读"
        return item

    if rule_id == "C03":
        # 抖音指数通常为 5-7 位数字，且不会超过千万级，避免误匹配时间戳/订单号等超长数字
        hits = re.findall(r"\b([1-9]\d{4,6})\b", text_blob)
        if hits:
            max_value = max(int(v) for v in hits)
            item["key_value"] = f"最大候选指数={max_value}"
            item["result"] = "通过" if max_value > 50000 else "不通过"
            item["note"] = "基于页面文本中的 5-7 位数字做基础阈值判断，已排除超长数字，仍建议人工复核"
        else:
            item["result"] = MANUAL_RESULT
            item["note"] = "已有抖音数据文件，但未提取到可用于阈值判断的数值"
        return item

    item["result"] = MANUAL_RESULT
    item["note"] = "已采集到所需数据，需人工结合证据判读"
    return item


def evaluate_stage(stage: int, files_by_source: dict[str, list[Path]], payloads: dict[str, list[dict]]) -> list[dict]:
    items = []
    for rule_id, rule in EVALUATION_RULES.items():
        if rule["stage"] != stage:
            continue
        item = build_empty_item(rule_id, rule)
        items.append(evaluate_rule(rule_id, item, rule, files_by_source, payloads))
    return items


def summarize_final_verdict(stage_results: dict, terminated: bool) -> str:
    if terminated:
        return "NO GO"

    all_items = [item for stage in stage_results.values() for item in stage["items"]]
    if any(item["result"] == NEEDS_DATA_RESULT for item in all_items):
        return "需补充数据"
    if any(item["result"] == MANUAL_RESULT for item in all_items):
        return "待人工复核"
    if all_items and all(item["result"] == "通过" for item in all_items):
        return "GO"
    return "待人工复核"


def main() -> None:
    parser = argparse.ArgumentParser(description="按 3.1 版评估框架执行产品评估")
    parser.add_argument("--product", required=True, help="产品名称")
    parser.add_argument("--approval-number", help="批准文号（可选）")
    parser.add_argument("--data-dir", help="已采集数据目录（不传则从默认日志目录读取）")
    parser.add_argument("--stage", choices=["1", "2", "3", "all"], default="all", help="执行阶段：1/2/3/all，默认 all")
    parser.add_argument("--no-auto-login", action="store_true", help="禁用自动引导登录；缺少登录态时仅报告缺口")
    parser.add_argument("--no-auto-fetch", action="store_true", help="禁用自动补采；缺少数据文件时仅报告缺口")
    parser.add_argument("--json", dest="output_json", action="store_true", help="输出 JSON 格式")
    args = parser.parse_args()

    print(f"🚀 开始评估: {args.product}", file=sys.stderr)
    print(f"   评估框架: 3.1 版 | 阶段: {args.stage}", file=sys.stderr)

    print("🔍 检查平台登录状态...", file=sys.stderr)
    sessions = check_sessions()

    data_dir = Path(args.data_dir) if args.data_dir else None
    stages_to_run = [1, 2, 3] if args.stage == "all" else [int(args.stage)]

    files_by_source = collect_data_files(data_dir, args.product)
    missing_login_platforms = collect_missing_login_platforms(stages_to_run, files_by_source)
    sessions = ensure_sessions_for_platforms(missing_login_platforms, sessions, args.output_json or args.no_auto_login)

    auto_fetch_missing_sources(
        stages_to_run,
        files_by_source,
        sessions,
        args.product,
        args.approval_number,
        not (args.output_json or args.no_auto_fetch),
    )

    # 登录或补采完成后重新读取本地数据文件，避免前后状态不一致
    files_by_source = collect_data_files(data_dir, args.product)
    payloads = load_source_payloads(files_by_source)

    evaluation_result = {
        "product": args.product,
        "approval_number": args.approval_number,
        "evaluation_date": datetime.now().strftime("%Y-%m-%d"),
        "framework_version": "3.1",
        "engine_mode": "semi-automatic",
        "stages_executed": stages_to_run,
        "final_verdict": None,
        "terminated_by": None,
        "data_sources_loaded": {source: len(files) for source, files in files_by_source.items()},
        "stage_results": {},
    }

    terminated = False
    for stage in stages_to_run:
        if terminated:
            break

        print(f"\n📋 执行第 {stage} 阶段...", file=sys.stderr)
        items = evaluate_stage(stage, files_by_source, payloads)

        for item in items:
            if item["rule"] in HARD_NO_GO_RULES and item["result"] == "不通过":
                evaluation_result["terminated_by"] = item["rule"]
                terminated = True
                print(f"🛑 硬性 NO GO: {item['rule']} {item['name']}", file=sys.stderr)
                break

        evaluation_result["stage_results"][f"stage_{stage}"] = {
            "items": items,
            "total": len(items),
            "passed": sum(1 for i in items if i["result"] == "通过"),
            "failed": sum(1 for i in items if i["result"] == "不通过"),
            "manual_review": sum(1 for i in items if i["result"] == MANUAL_RESULT),
            "missing_data": sum(1 for i in items if i["result"] == NEEDS_DATA_RESULT),
        }

    evaluation_result["final_verdict"] = summarize_final_verdict(evaluation_result["stage_results"], terminated)

    result_file = LOG_DIR / f"evaluation-{args.product}-{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
    result_file.write_text(json.dumps(evaluation_result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n📄 评估结果已保存: {result_file}", file=sys.stderr)

    if args.output_json:
        print(json.dumps(evaluation_result, ensure_ascii=False, indent=2))
    else:
        print(f"\n{'=' * 50}")
        print(f"产品: {evaluation_result['product']}")
        print(f"评估日期: {evaluation_result['evaluation_date']}")
        print(f"最终结论: {evaluation_result['final_verdict']}")
        if evaluation_result["terminated_by"]:
            print(f"终止原因: {evaluation_result['terminated_by']}")
        for stage_key, stage_data in evaluation_result["stage_results"].items():
            print(f"\n{stage_key}: 共 {stage_data['total']} 项")
            print(
                "  通过: {passed} | 不通过: {failed} | 待人工判读: {manual_review} | 需补充数据: {missing_data}".format(
                    **stage_data
                )
            )
        missing_platforms = [p for p, s in sessions.items() if not s.get("has_session") and p not in PUBLIC_SOURCES]
        if missing_platforms:
            print("\n⚠️  以下平台未登录，可能影响后续数据采集:")
            for platform in missing_platforms:
                print(f"   - {platform}: python scripts/platform-auth/login.py --platform {platform} --manual")


if __name__ == "__main__":
    main()
