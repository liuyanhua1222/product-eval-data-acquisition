# data-acquisition — 多平台数据采集

## 模块说明

使用已登录的平台会话，从各数据源采集产品评估所需的结构化数据。执行前需确认对应平台已登录（通过 `platform-auth/check_session.py` 验证）。

---

## 适用场景

- 评估新产品前采集批文、市场、电商、学术、医生资源等多维度数据
- 对单一数据源进行专项查询
- 交叉验证不同平台的同类数据

---

## 数据源与覆盖规则

| 脚本 | 数据源 | URL | 覆盖评估规则 | 登录要求 |
|------|--------|-----|------------|---------|
| `fetch_nmpa.py` | 国家药监局 | https://www.nmpa.gov.cn/datasearch/home-index.html#category=yp | A00/A01/A04/A09/A10/F01/F02/H09 | 无需登录（公开数据） |
| `fetch_nhsa.py` | 国家医保局 | https://www.nhsa.gov.cn/ | A00（医保类别） | 无需登录（公开数据） |
| `fetch_yaozh.py` | 药智网 | https://db.yaozh.com/ | A00/A01/A04/A08/A09/A10/B01/B02/F01/F02 | 推荐登录（VIP 解锁更多字段） |
| `fetch_dingxiangyuan.py` | 丁香园 | https://drugs.dxy.cn/ | A00/A08/B01/B02/E01/E02/E03/G01/G02 | 无需登录（说明书公开） |
| `fetch_kaisi.py` | 开思数据 | https://agent.sinohealth.com/chis | A02/A05/A06/D01-D04/H01-H11 | 必须登录 |
| `fetch_ecommerce.py` | 京东 / 天猫 / 美团 / 京东到家 / 饿了么 | 各平台站内 | A02/A03/A06/A07/C04/I03/I04 | 推荐登录 |
| `fetch_douyin.py` | 抖音创作服务平台 | https://creator.douyin.com/creator-micro/creator-count/arithmetic-index | B03/C03/J02 | 必须登录 |
| `fetch_juliang.py` | 巨量算数 | https://trend.moutai.com/ | B03/C03/J02 | 推荐登录（与抖音共用账号） |
| `fetch_xiaohongshu.py` | 小红书 | https://www.xiaohongshu.com/search_result | B03/C04/J02 | 推荐登录 |
| `fetch_literature.py` | PubMed / 万方 / 知网 | pubmed.ncbi.nlm.nih.gov 等 | C01/C02/E01/E02/E03/G01/G02/I01/I02/J01 | PubMed 无需登录 |
| `fetch_guideline.py` | 中华医学会 / 丁香园指南 / 中国医师协会 | cma.org.cn / guide.dxy.cn 等 | E01/E02/I06/I07 | 无需登录（大部分公开） |
| `fetch_doctor.py` | 抖音 / 视频号 | 抖音站内搜索 | K01/K02 | 必须登录抖音 |

---

## 动作列表

### fetch_yaozh — 采集药智网数据

**鉴权模式**: `access-token`

**输入**:

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| `--product` | string | 是 | 产品名称或 API 名称 |
| `--approval-number` | string | 否 | 批准文号，有则优先精确查询 |
| `--wait` | int | 否 | 页面等待时间（ms），默认 5000 |

**输出字段**: 批准文号、企业名称、剂型、规格、批准日期、医保类别、批文状态

---

### fetch_kaisi — 采集开思数据市场数据

**鉴权模式**: `access-token`

**输入**:

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| `--product` | string | 是 | 产品名称或品类关键词 |
| `--category` | string | 否 | 品类筛选，如"心脑血管" |
| `--wait` | int | 否 | 页面等待时间（ms），默认 8000 |

**输出字段**: B2C 规模（近三年）、线下药店规模（近三年）、同比、Top3 品牌份额、CR3、厂家数、品牌数、盒单价、日服用成本、行业平均转换率、平均客单价

---

### fetch_ecommerce — 采集电商平台数据

**鉴权模式**: `access-token`

**输入**:

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| `--product` | string | 是 | 搜索关键词 |
| `--platform` | string | 否 | `jd`/`tmall`/`meituan`/`all`，默认 `all` |
| `--pages` | int | 否 | 采集页数，默认 3 |

**输出字段**: 价格、评价数、好评率、店铺名、链接数、付款人数、是否有付费推广资源位（秒杀/闪购/百亿补贴）、O2O 蜂窝覆盖率

---

### fetch_douyin — 采集抖音关键词指数

**鉴权模式**: `access-token`

**输入**:

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| `--keywords` | string | 是 | 关键词，多个用逗号分隔（最多 3 个） |
| `--days` | int | 否 | 查询天数，默认 30 |

**输出字段**: 搜索指数均值、综合指数均值、同比、环比、趋势数据（用于 C03 阈值判断：均值 ≥ 5 万为通过）

---

### fetch_literature — 采集学术文献数据

**鉴权模式**: `nologin`（PubMed）/ `access-token`（万方/知网）

**输入**:

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| `--query` | string | 是 | 检索词，如"aspirin cardiovascular prevention" |
| `--source` | string | 否 | `pubmed`/`wanfang`/`cnki`，默认 `pubmed` |
| `--limit` | int | 否 | 返回条数，默认 20 |

**输出字段**: 标题、期刊、年份、IF（如有）、摘要、PMID/DOI

---

### fetch_doctor — 采集医生资源数据

**鉴权模式**: `access-token`（抖音）

**输入**:

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| `--disease` | string | 是 | 目标疾病/适应症，如"黄褐斑" |
| `--department` | string | 否 | 垂直科室，如"皮肤科" |
| `--platform` | string | 否 | `douyin`/`shipinhao`/`all`，默认 `douyin` |

**输出字段**: 可合作医生数量、垂直科室医生数量、可用于适应症科普医生数量、账号粉丝总量（用于 K01/K02）

---

## 约束

- 执行前必须通过 `platform-auth/check_session.py` 确认登录态有效
- 采集结果以 JSON 格式输出到 stdout，同时写入 `.cms-log/log/product-eval-data-acquisition/`
- 开思数据是 SPA 应用，直接访问子页面会 404，需通过主页搜索框触发
- `web_fetch` 对国内医药类站点几乎全部封锁，所有国内平台均使用 `browser` tool 采集
- 电商运营能力判断标准（A03/A07）：B2C 弱运营 = 官方店铺+链接总数 < 10 个，或主图/详情页仅实拍堆砌，或无秒杀/闪购/百亿补贴资源位；O2O 弱运营 = 无智搜/严选/智投付费推广，或蜂窝覆盖率 < 30%
