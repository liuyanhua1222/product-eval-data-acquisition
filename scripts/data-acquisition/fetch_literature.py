"""
fetch_literature.py — 采集学术文献数据（PubMed / 万方 / 知网）

鉴权模式: nologin（PubMed）/ access-token（万方/知网）
依赖: requests（pip install requests）

覆盖评估规则: C01/C02/E01/E02/E03/G01/G02

用法:
  python fetch_literature.py --query "aspirin cardiovascular prevention"
  python fetch_literature.py --query "阿司匹林 心血管" --source wanfang --limit 10
  python fetch_literature.py --query "aspirin" --source pubmed --limit 20 --json
"""

import argparse
import json
import sys
import time
import urllib.parse
from datetime import datetime
from pathlib import Path

import requests

LOG_DIR = Path(".cms-log/log/product-eval-data-acquisition")
LOG_DIR.mkdir(parents=True, exist_ok=True)

PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

TIMEOUT = 30
MAX_RETRIES = 3
RETRY_INTERVAL = 1


def call_pubmed_api(url: str, params: dict) -> dict:
    """调用 PubMed E-utilities API，带重试。"""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, params=params, timeout=TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            if attempt < MAX_RETRIES:
                print(f"⚠️  第 {attempt} 次请求失败，{RETRY_INTERVAL}s 后重试: {e}", file=sys.stderr)
                time.sleep(RETRY_INTERVAL)
            else:
                raise


def fetch_pubmed(query: str, limit: int) -> dict:
    """通过 PubMed E-utilities API 检索文献。"""
    # Step 1: 搜索获取 PMID 列表
    search_params = {
        "db": "pubmed",
        "term": query,
        "retmax": limit,
        "retmode": "json",
        "sort": "relevance",
    }
    search_result = call_pubmed_api(PUBMED_SEARCH_URL, search_params)
    id_list = search_result.get("esearchresult", {}).get("idlist", [])
    total_count = int(search_result.get("esearchresult", {}).get("count", 0))

    if not id_list:
        return {
            "success": True,
            "source": "pubmed",
            "query": query,
            "total_count": 0,
            "records": [],
        }

    # Step 2: 获取摘要信息
    fetch_params = {
        "db": "pubmed",
        "id": ",".join(id_list),
        "retmode": "json",
    }
    fetch_result = call_pubmed_api(PUBMED_FETCH_URL, fetch_params)
    uids = fetch_result.get("result", {}).get("uids", [])

    records = []
    for uid in uids:
        item = fetch_result["result"].get(uid, {})
        records.append({
            "pmid": uid,
            "title": item.get("title", ""),
            "journal": item.get("fulljournalname", item.get("source", "")),
            "pub_date": item.get("pubdate", ""),
            "authors": [a.get("name", "") for a in item.get("authors", [])[:3]],
            "doi": next(
                (a.get("value", "") for a in item.get("articleids", []) if a.get("idtype") == "doi"),
                "",
            ),
        })

    return {
        "success": True,
        "source": "pubmed",
        "source_url": "https://pubmed.ncbi.nlm.nih.gov",
        "query": query,
        "total_count": total_count,
        "returned_count": len(records),
        "query_date": datetime.now().strftime("%Y-%m-%d"),
        "records": records,
    }


def fetch_wanfang(query: str, limit: int) -> dict:
    """采集万方数据文献（主页搜索，无需账号）。"""
    encoded_query = urllib.parse.quote(query)
    search_url = f"https://s.wanfangdata.com.cn/paper?q={encoded_query}&s={limit}"

    return {
        "success": True,
        "source": "wanfang",
        "source_url": search_url,
        "query": query,
        "query_date": datetime.now().strftime("%Y-%m-%d"),
        "note": "万方数据主页可搜索，全文查看需账号。请使用 browser tool 访问以下 URL 获取完整结果。",
        "browser_url": search_url,
    }


def fetch_cnki(query: str, limit: int) -> dict:
    """采集知网CNKI文献（主页搜索，无需账号）。"""
    encoded_query = urllib.parse.quote(query)
    search_url = f"https://www.cnki.net/kns/defaultresult/index?DBCODE=CJFD&kw={encoded_query}"

    return {
        "success": True,
        "source": "cnki",
        "source_url": search_url,
        "query": query,
        "query_date": datetime.now().strftime("%Y-%m-%d"),
        "note": "知网主页可搜索，全文下载需账号。请使用 browser tool 访问以下 URL 获取完整结果。",
        "browser_url": search_url,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="采集学术文献数据")
    parser.add_argument("--query", required=True, help="检索词，如 'aspirin cardiovascular prevention'")
    parser.add_argument(
        "--source",
        choices=["pubmed", "wanfang", "cnki"],
        default="pubmed",
        help="数据源：pubmed/wanfang/cnki，默认 pubmed",
    )
    parser.add_argument("--limit", type=int, default=20, help="返回条数，默认 20")
    parser.add_argument("--json", dest="output_json", action="store_true", help="输出 JSON 格式")
    args = parser.parse_args()

    print(f"🔍 查询 {args.source}: {args.query}", file=sys.stderr)

    if args.source == "pubmed":
        result = fetch_pubmed(args.query, args.limit)
    elif args.source == "wanfang":
        result = fetch_wanfang(args.query, args.limit)
    else:
        result = fetch_cnki(args.query, args.limit)

    if result.get("success"):
        log_file = LOG_DIR / f"{args.source}-{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
        log_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"📄 结果已保存: {log_file}", file=sys.stderr)

    if args.output_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if result["success"]:
            print(f"\n✅ {args.source} 查询成功")
            print(f"   检索词: {result['query']}")
            if "total_count" in result:
                print(f"   总记录数: {result['total_count']}")
                print(f"   返回记录数: {result.get('returned_count', 0)}")
                for r in result.get("records", [])[:3]:
                    print(f"\n   [{r.get('pmid', '')}] {r.get('title', '')[:80]}")
                    print(f"   期刊: {r.get('journal', '')} | 年份: {r.get('pub_date', '')}")
            if result.get("browser_url"):
                print(f"\n   请用 browser tool 访问: {result['browser_url']}")
        else:
            print(f"\n❌ 查询失败: {result.get('error', '未知错误')}")


if __name__ == "__main__":
    main()
