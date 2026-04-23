# data-acquisition 脚本索引

## 脚本清单

| 脚本 | 用途 | 鉴权模式 | 覆盖规则 |
|------|------|---------|---------|
| `fetch_yaozh.py` | 采集药智网批文与说明书数据 | access-token | A00/A01/A04/A08/A09/A10/B01/B02/F01/F02 |
| `fetch_kaisi.py` | 采集开思CHIS市场数据 | access-token | A02/A05/A06/D01-D04/H01-H11 |
| `fetch_ecommerce.py` | 采集京东/天猫电商数据 | access-token | A02/A03/A06/A07/C04 |
| `fetch_douyin.py` | 采集抖音关键词指数 | access-token | B03/C03/J02 |
| `fetch_literature.py` | 采集PubMed/万方/知网文献 | nologin（PubMed）/ access-token（万方/知网） | C01/C02/E01/E02/E03/G01/G02 |

---

## 鉴权前置条件

- 执行前先运行 `platform-auth/check_session.py` 确认对应平台已登录
- `fetch_literature.py --source pubmed` 无需登录，直接运行
- 其他脚本需要对应平台的有效 Cookie（通过 `platform-auth/login.py` 获取）

---

## 运行方式

```bash
# 采集药智网批文数据
python scripts/data-acquisition/fetch_yaozh.py --product 门冬氨酸钙片

# 采集开思CHIS市场数据
python scripts/data-acquisition/fetch_kaisi.py --product 阿司匹林 --category 心脑血管

# 采集京东+天猫电商数据
python scripts/data-acquisition/fetch_ecommerce.py --product 阿司匹林 --pages 3

# 仅采集京东
python scripts/data-acquisition/fetch_ecommerce.py --product 阿司匹林 --platform jd

# 采集抖音关键词指数（最多3个关键词）
python scripts/data-acquisition/fetch_douyin.py --keywords "阿司匹林,心脑血管,血栓"

# 采集PubMed文献（无需登录）
python scripts/data-acquisition/fetch_literature.py --query "aspirin cardiovascular" --limit 20

# 采集万方文献
python scripts/data-acquisition/fetch_literature.py --query "阿司匹林 心血管" --source wanfang
```

---

## 返回说明

所有脚本支持 `--json` 参数输出结构化 JSON，结果同时写入 `.cms-log/log/product-eval-data-acquisition/`。

```json
// fetch_yaozh.py 输出示例
{
  "success": true,
  "product": "阿司匹林",
  "query_date": "2026-04-23",
  "source": "药智网 db.yaozh.com",
  "record_count": 934,
  "records": [...]
}
```

---

## 依赖

- `fetch_yaozh.py`：`playwright`（`pip install playwright && playwright install chromium`）
- `fetch_kaisi.py`：`playwright`
- `fetch_ecommerce.py`：`playwright`
- `fetch_douyin.py`：`playwright`
- `fetch_literature.py`：`requests`（`pip install requests`）
