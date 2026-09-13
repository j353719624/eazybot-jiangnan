---
name: portfolio-review
description: >
  日常自选股复盘日报生成器。自动拉取用户 Gangtise 自选股池的当日行情、资金流向、公告、研报线索和投研日程，
  生成结构化 Markdown 复盘日报 + 可视化 HTML。数据全部来自 Gangtise（data / file / agent / kb）。
  **触发场景**：用户说"生成自选股复盘"、"出日报"、"跑一下复盘"、"今天的复盘"、"portfolio review"、
  "给我看看今天的持仓"、"自选股表现如何"、"出个复盘报告"。
  注意：脚本会自动提取**执行者自己的自选股**（通过 stockpool.py --all），不会写死 pool_id，
  因此分享给同事后每个人跑的是自己配的自选股。
metadata:
  builtin_skill_version: "1.0"
---

# 自选股复盘 Skill

## 工作流

### Step 0：交易日确认（必须优先执行）
用 `exchange-calendars` 的 `snapshot` 命令判断当日是否为 A 股交易日：

```bash
cd skills/exchange-calendars
python3 scripts/trading_calendar.py snapshot "<当日 14:00>" -m A股
# 返回 is_trading_day: true → 继续；false → 跳过
```

仅当 `is_trading_day: true` 时才继续执行。
**注意：** 复盘日报在每日 **16:00（BJT）** 运行，此时 A 股已收盘（15:00）、港股已收盘（16:00），Gangtise `industry_indicator` 的"当日值"指标数据均已完备。

### Step 1：运行数据采集脚本
```bash
cd skills/portfolio-review
python3 scripts/collect_data.py --date <交易日>
```
脚本会自动：
- 拉取**执行者本人的自选股**（`stockpool.py --all`）
- 拉取当日行情 K 线 → `QUOTES.csv`（**覆盖 A 股 + 港股 + 美股**；美股使用前一日数据，因 BJT 17:00 美盘尚未收盘）
- 拉取 A 股资金流向 → `FUND_FLOW.csv`
- 查询公司公告
- 查询投研线索 → `CLUES.md`
- 查询投研日程（未来一周）→ `CALENDAR.md`
- 拉取大盘指数数据（上证指数/科创50/恒生指数）→ 写入 `data.json` 的 `index_data` 字段
- 拉取两市成交额（沪市+深市）→ 写入 `data.json` 的 `market_turnover` 字段

脚本输出目录：
```
workspace/gangtise/portfolio_review/YYYY-MM-DD/
├── data.json          → 结构化摘要（含 index_data, market_turnover 字段）
├── QUOTES.csv         → 行情原始数据
├── FUND_FLOW.csv      → 资金流向原始数据
├── CLUES.md           → 投研线索
└── CALENDAR.md        → 投研日程
```

### Step 2：读取并解析数据
```bash
cat workspace/gangtise/portfolio_review/YYYY-MM-DD/data.json
```
读取各 CSV 做涨跌幅排名、板块归因等分析。

### Step 3：补充查询（Gangtise 三件套）
**优先级：Gangtise File → Gangtise Agent → Gangtise KB**

| 场景 | 推荐工具 | 命令示例 |
|------|----------|----------|
| 个股最新研报/观点 | **Gangtise File** `report.py` | `python3 scripts/report.py -k <个股名> -sd <近一周> -l 5` |
| 个股一句话投研摘要 | **Gangtise Agent** `agents.py -a stock-one-line-summary` | `python3 scripts/agents.py -a stock-one-line-summary --securities <代码>` |
| 热点话题/主题跟踪 | **Gangtise Agent** `hot_topic.py` | `python3 scripts/hot_topic.py -sd <当日> -ed <当日> --hot-category morning,afternoon,evening` |
| 市场观点、行业分析 | **Gangtise KB** `kb.py -q "..."` | `python3 scripts/kb.py -q "<关键词>"` |
| 个股投资逻辑 | **Gangtise Agent** `agents.py -a investment-logic` | `python3 scripts/agents.py -a investment-logic --security <名称>` |
| 公司公告详情 | **Gangtise File** `announcement.py` | `python3 scripts/announcement.py --securities <名称> -sd <当日> -ed <当日>` |
| 个股研报原文 | **Gangtise File** `opinion.py` / `summary.py` | `python3 scripts/opinion.py --securities <名称> -l 5` |

**注意：** 所有补充查询都从 `skills/<对应skill>/` 目录执行（需已安装岗底斯技能）。

### Step 4：编译复盘日报

#### 输出格式
- **Markdown：** `workspace/gangtise/portfolio_review/YYYY-MM-DD/review.md`
- **HTML：** `workspace/gangtise/portfolio_review/YYYY-MM-DD/review.html`

#### HTML 生成规范（重要，不可违反）
HTML 文件**必须**严格按照 `references/html-template.md` 模板生成，遵循以下规则：
1. **禁止**使用脚本将 Markdown 转换为 HTML（如Python替换式转换），必须直接手写HTML填入模板占位符
2. 模板中的 `{{PLACEHOLDER}}` 变量必须全部替换为实际数据
3. 盘面速览部分使用模板中的 `summary-row`（五项指标）、`mood-grid`（flex布局情绪框）
4. 大盘指数表格使用模板中的 `<table>` 结构，标注 up/down class
5. 后续各章节不写死格式，但风格需与模板一致（卡片、表格、事件条目等）
6. HTML 内容必须与 Markdown 报告**数据一致**，不允许两者数据冲突

---

## 日报结构模板

### 一、盘面速览

| 指标 | 数值 |
|------|------|
| 自选股池规模 | **XX 只**（通过 `stockpool.py --all` 动态获取） |
| 上涨/下跌/平盘 | X / X / X |
| 平均涨跌幅 | xx% |
| 涨跌幅中位数 | xx% |

**大盘指数表格（数据全部走 Gangtise `industry_indicator`，不显示数据来源列）：**
- A 股三大指数：上证指数、深证成指、创业板指
- 科创板：科创50
- 港股：恒生指数、恒生科技

| 指数 | 收盘 | 涨跌幅 |
|------|------|--------|
| 上证指数 | xxxx.xx | **+x.xx%** |
| 深证成指 | xxxx.xx | **-x.xx%** |
| ... | ... | ... |

**指数数据获取（16:00 运行数据完备）：**
- **A股指数优先路径：** `quote.py --securities "000001.SH,399001.SZ,399006.SZ,000688.SH" -sd <日期> -ed <日期>`（上证指数、深证成指、创业板指、科创50）
  - `industry_indicator` 的 S25000024/S25000026 对 A 股指数可能返回 nan，quote.py 更可靠
- **港股指数（恒生指数 + 恒生科技指数 + 国企指数）：** 使用**新浪实时行情 API**（已在 `collect_data.py` 中实现）
  - 方式：Python urllib 请求 `https://hq.sinajs.cn/list=rt_hkHSI,rt_hkHSTECH,rt_hkHSCEI`
  - 需携带 `Referer: https://finance.sina.com.cn` 请求头
  - 返回结构化数据（开盘/昨收/最高/最低/收盘/涨跌/涨跌幅），可直接解析
  - 已验证：2026-07-22 恒生科技收盘 **4,668.23**（跌3.04%），恒生指数 24,892.66（跌0.95%）
  - **优势：** 只需简单 HTTP GET，不需要浏览器；返回数据是收市竞价后的最终收盘价
  - 报告中不出现数据来源名，仅写数值
  - ⚠️ `quote.py` **不支持恒生指数**（港股quote只返回个股00001.HK~89988.HK，不含指数）
- **两市成交额优先路径：** `industry_indicator` 沪市成交额（M00015740，亿元）+ 深市成交额（M00015743，亿元）= 两市合计（亿元）
  - **回退方案：** 当 industry_indicator 返回为空时，用 `quote.py --securities "000001.SH,399001.SZ"` 指数行情中的成交额字段
  - 上证指数成交额 = 沪市成交额（元→亿元÷1e8）
  - 深证成指成交额 = 深市成交额（元→亿元÷1e8）
  - 两个来源的数值误差通常 < 0.2%，可交叉验证

**市场情绪小框（`flex: 1` 充满整行）：**
- 成交额（万亿/百亿级）、较上日变化
- 涨停家数、封板率
- 下跌个股数
- 领涨行业

**文字表述分两段：**
- **【市场综述】** — 大盘表现 + 市场情绪 + 港股/海外（不含自选股信息）。**与【自选股综述】同字号、同颜色、同样式。**
- **【自选股综述】** — 自选股整体涨跌归因，当日分化格局的客观描述。**禁用"中性偏积极"等情绪标签。**

### 二、自选股涨跌榜

| # | 名称 | 代码 | 收盘价 | 涨跌幅 | 简评 |
|---|------|------|--------|--------|------|

**分类展示：**
- **涨幅 TOP 5**（附简评，可从 CLUES / 研报 / KB 中找原因）
- **跌幅 TOP 5**（同样附简评）
- **异动关注**（成交量异常、资金大幅进出、盘中异动）—放在涨跌榜末尾

### 三、行业/板块动态

从自选股所属行业分布角度，梳理当日主要板块表现。

**每个板块分两层：**

**行业要闻**（纯事实，不带机构名）
- 当日重要行业事件（确认是当天交易日资讯，禁止出现跨周/跨月幻觉）
- **来源说明：** 行业要闻来自实时财经资讯（非 Gangtise），但报告中**禁止出现 web_search / 财联社 / 同花顺 / 东方财富等任何来源表述**
- 禁止出现政治敏感词汇
- 语言简洁，不引用机构名

**机构点评**（仅观点内容，禁止出现机构及分析师署名）
- 从 Gangtise 三件套获取观点内容，去掉机构及分析师署名后直接引用

写法示例：
```
### 领涨方向：半导体 + AI算力

**行业要闻**
- 台积电Q2业绩大幅超预期：营收1.27万亿新台币（同比+36%），净利润7065.6亿（同比+77.4%），毛利率67.7%，HPC营收占66%，AI需求旺盛，上调资本开支至600-640亿美元
- WAIC 2026大会召开：算力底座升维，生态持续完善，国产模型迈入2-3万亿参数时代

**机构点评**
- AI需求支撑资本开支连续上调，封测/先进封装直接受益
- 算力竞争转向"每瓦产出"和"每百万Token成本"
```

### 四、公司公告 & 重要信息

从 `announcement.py` 和 CLUES 中提取：
- 业绩预告/快报
- 重大合同/订单
- 股东增减持
- 其他重大事项

如无公告，**统一写：**
```
今日自选股池（XX只）无相关公司重大公告披露。
```
**禁止**在报告中展示来源排查过程（如"Gangtise announcement.py → 未找到"、"财联社→ 未发现"等表述）。

**补充来源（如 `announcement.py` 无结果，按以下优先级）：**
1. **Gangtise FILE**：换其他文档类型重试（如 `opinion.py`、`summary.py`）
2. **Gangtise KB**：`kb.py -q "<证券名> 公告 <日期>"` 语义检索
3. 如 KB 有结果，用外部新闻交叉验证后使用（但报告中不体现来源名）

### 五、机构观点 & 投资逻辑

从 Gangtise 三件套获取（**时间范围：优先当日，当日内容不够则扩大至近3个交易日**）：
- **同一个标的的观点合并放在一起**，按标的名称组织，不要分机构列
- **标的必须是自选股标的**（禁止出现非自选股的板块名称如"半导体链"）
- 每个标的一段，多机构观点用"；"分隔
- 写法：`**宁德时代（300750.SZ）** 消费税利空出尽...；Q2-Q3单位利润持续提升...。`

### 六、核心主线展望

- 基于当前数据梳理 **短期主线方向**（3条左右），每条关联具体自选股
- **①、②、③ 数字图标 + 标题加粗**，与正文做区分
- **关联自选股另起一行**，缩进放在主线标题下方，格式：
  ```
  ① **主线标题**
     关联自选股：XXX、XXX、XXX
  ```
- 需要关注的风险点/催化点
- 克制、数据说话

### 七、投研日程（未来一周）

从 CALENDAR.md 汇总：
- 重点路演/调研/策略会
- 业绩会排期
- 论坛/会议
- **类型用文字**（路演/调研/策略会/论坛），**禁用图标**

---

## 写作规范（重要）

| 规范 | 要求 |
|------|------|
| 标题 | 用序号"一、二、三...", **禁用前缀图标**（📊🔺🔻💡📍等） |
| 数据来源 | "数据来源：Gangtise"，**不用"Gangtise 终端"** |
| 情绪标签 | **禁用"中性偏积极"**等情绪判断，改为客观描述 |
| 团队名 | **禁止出现机构及分析师名称**（如"xx证券"、"xx团队"、"xx分析师"等），观点内容直接引用，不带署名 |
| 公告为空 | **统一写** "今日自选股池（XX只）无相关公司重大公告披露。"，不展示排查过程 |
| 机构观点 | 按标的合并，不设机构列，标的必须是自选股盘中标的；**禁止出现机构或分析师署名** |
| 后市标题 | 改为"核心主线展望" |
| 日程类型 | 用文字，禁用图标 |
| 免责声明 | 文末用 `**免责声明：** 本报告内容仅供信息参考，不构成任何投资建议。任何依据本内容作出的投资决策，风险由投资者自行承担。市场有风险，投资需谨慎。` + 另起一行 `数据来源：Gangtise`，**不加"Generated by..."** |
| 港股美股 | 如自选池含港股/美股，涨跌榜同步纳入；美股日期用前一日（BJT 17:00 时美盘未收盘）；ADR（存托凭证）不支持 |
| **大盘指数** | **使用 Gangtise `industry_indicator`** 获取A股指数+恒生指数数据。去掉"数据来源"列，不展示来源名 |
| **行业/板块动态** | 分两层：**行业要闻**（纯事实，不带机构名）+ **机构点评**（仅观点内容，**禁止出现机构及分析师署名**） |
| **市场表述** | 盘面速览下分 **【市场综述】**（大盘）和 **【自选股综述】**（自选股），同字号/同颜色/同样式 |
| **成交额** | 从 Gangtise `industry_indicator` 获取沪市+深市成交额后加总，**禁止**使用外部来源数据 |
| **来源管控** | 报告中**禁止**出现以下词汇：web_search、财联社、同花顺、东方财富、百度等任何数据来源名 |
| **政治敏感** | 全文**禁止**出现政治敏感词汇。涉及地缘因素时用经济角度表述（如"原油供应扰动"替代"中东局势"） |
| **交易日确认** | 所有引用的实时资讯必须确认是**当天交易日**的事件，禁止跨周/跨月事件幻觉 |
| **HTML生成** | 必须严格按 `references/html-template.md` 模板手写，禁止脚本转换Markdown→HTML |

---

## 写作风格

参考 SOUL.md 中的金融日报风格：
- **专业但可读** — 结构化、重点突出、适合快速扫读
- **数据驱动** — 每个结论背后必须有数据支撑
- **克制不越界** — 不下买卖结论，只做客观归因
- **动态过渡** — 段落之间用当日市场特点引入，不用"再来看XX"这种模板套话
- **合规** — 禁用"外围市场"等表述，用"海外市场"

---

## Cron 定时任务

当用户要求"每天16:00自动跑"时，用 cron skill 创建 agent 类型任务：

```bash
eazybot cron create \
  --agent-id <agent_id> \
  --type agent \
  --schedule-type cron \
  --name "自选股复盘" \
  --cron "30 16 * * 1-5" \
  --channel <channel> \
  --target-user <user> \
  --target-session <session> \
  --text "请生成今日自选股复盘日报（先确认交易日，非交易日跳过）" \
  --save-result-to-inbox
```

注意：
- cron 表达式 `30 16 * * 1-5` = 交易日（周一到周五）**16:30**
- A 股 15:00 收盘 + 港股 16:00 收盘 + 港股收市竞价 16:08~10 结束，16:30 运行可确保获取收市竞价后最终收盘价 ✅
- **执行前必须先用 `exchange-calendars` 的 `snapshot` 确认当日为 A 股交易日**，非交易日自动跳过
- 如果任务涉及发送到特定渠道，先确认 channel / target-user / target-session

---

## 分享给同事须知

本 Skill 通过 `stockpool.py --all` 拉取**执行者本人的自选股**，不会写死 pool_id。所以：
1. ✅ 分享给同事后，他们配置自己的 Gangtise 凭证，跑的是他们自己的自选股
2. ❌ 如果同事没配 Gangtise 凭证，跑不起来
3. ❌ 如果 Skill 里写死了 `--pool xxxx`，所有人都跑同一个池子

**建议首次使用前先测试：**
```bash
python3 scripts/collect_data.py --date <前一个交易日>
```
确认数据能正常拉取。
