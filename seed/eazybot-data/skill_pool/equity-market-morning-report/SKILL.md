---
name: equity-market-morning-report
description: >
  面向资管买方分析师的 A 股二级市场早报。按「市场总览 3×3 → 宏观要闻(5条) → 产业要闻(科技/新能源/消费/医药/周期) → 热点话题深度(≥5条) → 首席观点精选(≥5条) → 重点股票池(≤10只,赛道细分)」六段式输出，数据全部来自 Gangtise 终端，禁止出现任何数据终端品牌名。
  当用户提及"资管早报""买方早报""产业早报""二级市场早报""行业早报""今日热点""出早报""morning briefing""industry briefing"时必须使用此技能。
metadata:
  builtin_skill_version: "1.0"
---

# 二级市场早报

## 定位

面向资管机构买方分析师的盘前产业快报。不是泛泛新闻汇总，是**盘面→宏观→产业→深度话题→首席观点→落到股票池**的完整逻辑链。

受众：每天开盘前需要快速扫一眼"昨天大盘怎么样、宏观有什么变化、我覆盖的赛道出了什么大事、首席怎么看、哪些票要关注"的买方研究员和基金经理。

---

## 🔒 数据合规红线

**禁止在报告中出现以下品牌名**（违者重写）：
- ❌ Wind / 万得
- ❌ 同花顺 / 东方财富
- ❌ 新浪财经 / 华尔街见闻
- ❌ 任何其他数据终端品牌名

**数据来源统一写**：`数据来源：Gangtise 数据终端 | 仅供参考，不构成投资建议`

**禁止内容**：
- ❌ 贪腐类内容、敏感政治内容
- ❌ 凭空出现没有来源的数字或事件
- ❌ 预测市场方向、推荐买卖（"建议买入/卖出"等）
- ❌ 出现非本周或非交易日的事件（如非农数据幻觉）
- ❌ 「尚未公布」「修正」「补正」「更新为」「待确认」「数据待补」等补丁痕迹

---

## 数据源优先级体系

### 三层架构

```
第一层（优先）：Gangtise
├── quote.py       → A股/港股指数K线
├── fund_flow.py   → A股资金流向
├── hot_topic.py   → 热点话题
├── industry_indicator.py → 大宗商品/行业指标
├── kb.py          → 知识库检索（宏观/产业/首席观点）
├── opinion.py     → 首席观点直拉
└── agents.py      → 股票摘要/主题跟踪

第二层（补缺）：Gangtise KB 交叉检索
└── 港股美股指数 → 通过 kb.py 搜索「证券早晨快讯」「每日晨报」「港股点评」
                  等报告，提取指数收盘价

第三层（校验）：外部新闻交叉验证
├── kb.py 搜索「财联社 隔夜 全球要闻」「汇通财经」等独立金融新闻
└── 禁从新闻文本直接摘取数值，仅做方向性核对
```

### 数据源覆盖矩阵

| 数据类型 | 主数据源 | 校验源 | 校验要求 |
|----------|----------|--------|----------|
| A股指数K线 | Gangtise `quote.py` | Gangtise KB（每日晨报/晨会纪要）+ 财联社新闻 | 三源交叉验证 |
| A股资金流向 | Gangtise `fund_flow.py` | — | — |
| 恒生指数 | Gangtise `quote.py` | Gangtise KB（证券早晨快讯/港股点评）+ 财联社新闻 | 三源交叉验证 |
| 恒生科技 | Gangtise `quote.py` | Gangtise KB（证券早晨快讯/港股点评）+ 财联社新闻 | 三源交叉验证 |
| 标普500 | Gangtise EDB `M00006167` | Gangtise KB（每日晨报/证券早晨快讯）+ 财联社新闻 | 三源交叉验证（EDB按美东交易日日期存储） |
| 道琼斯 | Gangtise EDB `M00009829` | Gangtise KB（每日晨报/证券早晨快讯）+ 财联社新闻 | 三源交叉验证（EDB按美东交易日日期存储） |
| 纳斯达克 | Gangtise EDB `M00009828` | Gangtise KB（每日晨报/证券早晨快讯）+ 财联社新闻 | 三源交叉验证（EDB按美东交易日日期存储） |
| 热点话题 | Gangtise `hot_topic.py` | — | — |
| 宏观/产业要闻 | Gangtise KB检索 | 财联社/汇通财经新闻 | 方向性核对 |
| 大宗商品 | Gangtise `industry_indicator.py` | 实时行情接口（快速校验）+ 财联社新闻 | 双源验证 |
| 首席观点 | Gangtise File `opinion.py` | 优先本周最新，>7天用web_search补充 | 单源+时效校验 |
| 股票摘要 | Gangtise `stock-one-line-summary` | — | — |

---

## 核心原则

1. **盘面先行。** 早报开头必须有「市场总览」3×3网格——指数涨跌、成交额、资金方向、一句话市场状态。
2. **产业视角，不是新闻标题罗列。** 每条要跟 2-3 句逻辑分析——产业链传导、预期差、持续性判断。
3. **宁缺毋滥。** 某板块当日没有足够热点，就写 2-3 条，不凑数。
4. **热点话题深度要展开（≥5条）。** 完整呈现事件+逻辑+相关标的（**仅列名称，不用表格**）。
5. **首席观点必须注明日期。** 隐去分析师姓名和报告标题，仅保留核心观点+日期。
6. **股票池可落地。** 按赛道细分分组，最多10只，从当天热点动态提取。
7. **数据全部来自 Gangtise。** 港股美股指数也要通过Gangtise KB交叉验证获取，禁止写Wind/同花顺/新浪财经等终端品牌名。
8. **每条热点必须附带分析。** 产业链传导、预期差、持续性判断，三者至少写两点。

---

## 六大板块定义

| 序号 | 板块 | 覆盖范围 |
|------|------|----------|
| 一 | 宏观 | 货币政策、财政政策、经济数据、地缘政治、监管政策、海外宏观对 A 股的传导 |
| 二 | 科技 | AI/大模型、半导体/芯片、机器人/自动化、自动驾驶/智能汽车、低空经济、消费电子、光通信/算力、商业航天 |
| 三 | 新能源 | 光伏/硅料硅片/组件/逆变器、储能/电池、风电、锂电产业链、氢能、核电、固态电池 |
| 四 | 消费 | 食品饮料/白酒、家电/家居、汽车整车、零售/电商、旅游/免税/餐饮、纺织服装、新消费/IP 经济 |
| 五 | 医药 | 创新药/生物制药、CXO、医疗器械、中药、医疗服务/连锁、疫苗/血制品、CGT |
| 六 | 周期 | 有色金属/贵金属、煤炭、钢铁、化工、建材、电力/能源、航运/物流 |

---

## 执行流程

### 第 0 步：交易日确认

```bash
cd skills/exchange-calendars && python3 scripts/trading_calendar.py is_open "A股" {前一日}
cd skills/exchange-calendars && python3 scripts/trading_calendar.py is_open "A股" {当日}
```

- 当日非交易日 → 提示"今日 A 股休市"，不生成早报
- 当日是交易日 → 正常执行
- 每天确认前一日/当日是否交易日，防止跨周跨月幻觉

### 第 1 步：并行拉取数据（七路）

#### 1.1 A股行情速览（Gangtise quote.py + KB + 财联社三源验证）

```bash
# 主数据源
cd skills/gangtise-data && python3 scripts/quote.py \
  --securities 上证指数,深证成指,创业板指,科创50,沪深300,中证500,中证1000,上证50,北证50 \
  -sd {前一日} -ed {前一日}

# 校验源1：Gangtise KB（每日晨报/晨会纪要）
cd skills/gangtise-kb && python3 scripts/kb.py \
  -q "A股 收盘 上证指数 深证成指 创业板 7月{前一日}日" \
  -sd {前2日} -ed {前一日} -l 3

# 校验源2：财联社新闻（通过KB搜索）
cd skills/gangtise-kb && python3 scripts/kb.py \
  -q "财联社 收评 沪指 深成指 创业板 {M}月{D}日" \
  -sd {前2日} -ed {前一日} -l 3
```

北证50成交额单独提取相加，得全市场成交额。三源数据比对一致后方可写入。

#### 1.2 港股指数（Gangtise quote.py + KB + 财联社三源验证）

```bash
# 主数据源：Gangtise quote.py（需已安装岗底斯技能 gangtise-data）
cd skills/gangtise-data && python3 scripts/quote.py \
  --securities 恒生指数,恒生科技 \
  -sd {前一日} -ed {前一日}

# 校验源1：Gangtise KB
cd skills/gangtise-kb && python3 scripts/kb.py \
  -q "港股收盘 恒生指数 恒生科技 7月{前一日}日" \
  -sd {前2日} -ed {前一日} -l 5

# 校验源2：财联社新闻
cd skills/gangtise-kb && python3 scripts/kb.py \
  -q "财联社 港股 收盘 恒指 恒生科技 {M}月{D}日" \
  -sd {前2日} -ed {前一日} -l 3
```

三源数据比对一致后写入。

#### 1.3 美股指数（Gangtise EDB主力 + KB + 财联社三源验证）

```bash
# 主数据源：Gangtise EDB（industry_indicator）
# 标普500 M00006167 | 纳斯达克 M00009828 | 道琼斯 M00009829
# 注意：EDB按美东交易日日期存储，需用美东日期查询。
# 如7/24 BJT报告查询US 7/23收盘（美东日期），EDB中存为20260723：
cd skills/gangtise-data && python3 scripts/industry_indicator.py -m get \
  --indicators M00006167,M00009828,M00009829 \
  -sd {前1日(美东)} -ed {当日(美东)}   # 如-sd 2026-07-23 -ed 2026-07-24

# 校验源1：Gangtise KB（每日晨报/证券早晨快讯）
cd skills/gangtise-kb && python3 scripts/kb.py \
  -q "美股 收盘 道指 标普 纳指 7月{前一日}日" \
  -sd {前2日} -ed {前一日} -l 5

# 校验源2：财联社新闻
cd skills/gangtise-kb && python3 scripts/kb.py \
  -q "财联社 隔夜 美股 收盘 道指 标普 纳指 {M}月{D}日" \
  -sd {前2日} -ed {前一日} -l 3
```

注意时间线：美东收盘对应北京时间次日凌晨。在早8点30分运行报告时，美东当日收盘数据已可用。EDB中日期为美东交易日日期，查询范围需将**结束日期向后延一天**（如查7/23美东收盘，用 `-sd 2026-07-23 -ed 2026-07-24`）。

#### 1.3 全市场资金流向（fund_flow.py）

```bash
cd skills/gangtise-data && python3 scripts/fund_flow.py \
  --all-market -sd {前一日} -ed {前一日} --limit 8000
```

汇总 CSV 的「主力净流入（单位：元）」字段得到全市场主力资金净流入。

#### 1.4 热点话题列表（hot_topic）——核心素材

```bash
cd skills/gangtise-agent && python3 scripts/hot_topic.py \
  -sd {前一日} -ed {前一日} \
  --hot-category morning,evening \
  --with-securities \
  --page-size 200
```

#### 1.5 宏观知识库检索（KB）

```bash
cd skills/gangtise-kb && python3 scripts/kb.py \
  -q "宏观 货币政策 财政政策 美联储 降息 经济数据 地缘" \
  -sd {前2日} -ed {前一日} -l 5 \
  --file-types "首席观点,研究报告,产业公众号"
```

**宏观要闻验证**：
- KB检索结果 → 必须用 `kb.py` 搜索「财联社 隔夜 全球要闻」「汇通财经」等方向校验
- 若KB中财联社新闻不足 → 用 `web_search` 搜索"财联社 隔夜全球要闻 {日期}"补充
- **禁止从新闻文本直接摘取数值**，仅核对事件方向

#### 1.6 产业KB检索（六板块）

```bash
cd skills/gangtise-kb && python3 scripts/kb.py \
  -q "{板块关键词}" \
  -sd {前2日} -ed {前一日} -l 5 \
  --file-types "首席观点,研究报告,产业公众号"
```

| 板块 | KB 检索词 |
|------|-----------|
| 科技 | `科技 AI 半导体 芯片 机器人 算力 国产替代 大模型 商业航天` |
| 新能源 | `新能源 光伏 储能 锂电池 固态电池 风电 电池消费税` |
| 消费 | `消费 白酒 食品饮料 家电 旅游 零售 汽车 社零` |
| 医药 | `医药 创新药 CXO 医疗器械 集采 医保 生物制药 CGT` |
| 周期 | `周期 有色金属 煤炭 钢铁 化工 航运 石油 大宗商品` |

**产业要闻验证**：
- 每条产业要闻必须走KB检索 → web_search（财联社/金十新闻）方向性确认
- 确认方向一致后方可写入

#### 1.7 首席观点/策略研判（Gangtise File — opinion.py）

```bash
cd skills/gangtise-agent && python3 scripts/agents.py \
  -a earnings-review \
  --query "首席观点 策略研判 下半年 大类资产配置" \
  -sd {前7日} -ed {前一日}
```

**首席观点规则**：
- 优先使用 `gangtise-file` 的 `opinion.py` 直接拉取
- 若 opinion.py 无效 → `gangtise-kb` 搜索「首席观点 策略研判 A股」补充
- **必须隐去分析师姓名和报告标题**，仅提炼：核心观点 + 日期
- 优先取本周内最新数据
- 若KB返回时间过旧（>7天），用 `web_search` 补充最新观点
- 推荐写法：`观点：{提炼内容}| {M}月{D}日`

#### 1.8 股票摘要（stock-one-line-summary）

```bash
cd skills/gangtise-agent && python3 scripts/agents.py \
  -a stock-one-line-summary \
  --securities {股票1},{股票2},...
```

### 第 2 步：筛选与分类

- 将 hot_topic 结果按六大板块分类
- 从 KB 检索结果提取宏观要闻和产业深度观点
- 从首席观点结果精选最近 3 天内的核心观点

### 第 3 步：撰写早报（六段式结构）

#### 一、市场总览

**3×3网格**（9格按：上证/深证/创业板/恒生/恒生科技/科创50/标普/道琼斯/纳斯达克排列）：

```
| | 收盘 | 涨跌 | | 收盘 | 涨跌 | | 收盘 | 涨跌 |
|上证|x,xxx|+x%|恒生|x,xxx|+x%|标普|x,xxx|+x%|
|深证|x,xxx|+x%|恒生科技|x,xxx|+x%|道琼斯|x,xxx|+x%|
|创业板|x,xxx|+x%|科创50|x,xxx|+x%|纳斯达克|x,xxx|+x%|
```

全市场成交额，主力资金净流入/流出，一句话市场特征。

**港股美股指数数据格式**：
- 已公布数据 → 直接写入（如：恒指 25,143）
- 涨跌统一用「+x% / -x%」格式，港股美股均不用「+x.xx点」

#### 二、宏观要闻（5条）

每条结构：

```
### {事件标题}

**事件**：{一句话描述}
**分析**：{~100字逻辑梳理，不超过100字}
```

- **严格5条**，分析控制在100字内

#### 三、产业要闻

按科技、新能源、消费、医药、周期子标题展开。每条结构同上（事件 + 分析）。

- 不足3条的板块写1-2条，不凑数

#### 四、热点话题深度（≥5条）

从 hot_topic 选最热的 ≥5 个话题，每条完整展开：

```
### {热点标题}

**事件与逻辑**：{驱动事件 + 投资逻辑合并叙述，必须包含产业链传导、预期差、持续性判断}
**相关标的**：{仅列名称，如「中兴通讯、烽火通信」，不用表格}
```

- **禁止用表格展示标的**
- 每条必须附带分析（产业链传导/预期差/持续性判断，至少两点）

#### 五、首席观点精选（≥5条）

```
### {观点提炼标题}

{核心观点正文，2-4段} — {M}月{D}日
```

- **隐去分析师姓名和报告标题**
- 仅保留：核心观点 + 日期
- 来源统一写"Gangtise 数据终端"

#### 六、重点股票池（最多10只）

基于当天 hot_topic 核心标的和 KB 标的，按赛道细分分组：

| 赛道（细分） | 代码 | 名称 | 投资逻辑 |
|------|------|------|----------|
| AI算力 | 600000.SH | XX | 核心一句话逻辑 |
| 机器人 | 300000.SZ | XX | ... |
| 商业航天 | ... | ... | ... |
| 半导体 | ... | ... | ... |
| 新能源 | ... | ... | ... |
| 创新药 | ... | ... | ... |

- 赛道用细分名称（如"AI算力""机器人""商业航天""半导体设备""创新药"等）
- 最多10只

### 第 4 步：输出

```bash
output/二级市场早报_YYYYMMDD.md
output/二级市场早报_YYYYMMDD.html
```

---

## Markdown 模板

```markdown
# 🔍 二级市场早报

**{YYYY}年{M}月{D}日（周{X}）| 数据截至{M-1}月{D-1}日收盘**

---

## 一、市场总览

|  | 收盘 | 涨跌 |  | 收盘 | 涨跌 |  | 收盘 | 涨跌 |
|------|------|------|------|------|------|------|------|------|
| 上证指数 | x,xxx | +x% | 恒生指数 | x,xxx | +x% | 标普500 | x,xxx | +x% |
| 深证成指 | x,xxx | +x% | 恒生科技 | x,xxx | +x% | 道琼斯 | x,xxx | +x% |
| 创业板指 | x,xxx | +x% | 科创50 | x,xxx | +x% | 纳斯达克 | x,xxx | +x% |

> 全市场成交额：xx,xxx 亿 | 主力资金：净流入/流出 xxx 亿
> 特征：{一句话描述}

---

## 二、宏观要闻

### {事件标题}

**事件**：{一句话描述}
**分析**：{~100字}

...

---

## 三、产业要闻

### 科技

...

### 新能源

...

### 消费

...

### 医药

...

### 周期

...

---

## 四、热点话题深度

### {热点标题}

**事件与逻辑**：{驱动事件 + 投资逻辑（产业链传导/预期差/持续性判断）}
**相关标的**：{仅列出标的名称}

...

---

## 五、首席观点精选

### {观点标题}

{核心观点正文} — {M}月{D}日

...

---

## 六、重点股票池

| 赛道（细分） | 代码 | 名称 | 投资逻辑 |
|------|------|------|----------|
| AI算力 | 600000.SH | XX | ... |
| 机器人 | 300000.SZ | XX | ... |

---

*数据来源：Gangtise 数据终端 | 仅供参考，不构成投资建议*
```

---

## HTML 设计规范

面向移动端/平板快速浏览的纯平风格设计：

- **整体布局**：单栏，max-width 640px 居中，白底容器 `.c`
- **头部**：深蓝渐变 `#1a365d → #2d5a87`，白字，标题居中，日期次行
- **一级标题（一~六）**：`.stt` — 1.1em、加粗、#1a365d，底部 2px 深蓝线
- **二级标题（产业子标题）**：`.sh` — 1em、semibold、#2d5a87，左侧 3px 深蓝条纹
- **事件卡片**：`.bx` — 浅灰底 `#f8fafc` + `1px #e5e7eb` 边框+圆角
- **标签"事件""分析"**：统一灰色 `#475569`，事件标题用 `.item-label` 深蓝色
- **热点话题深度卡片**：`.feature-block` — 浅灰底+边框，大圆角
- **首席观点卡片**：`.chief-block` — 浅蓝底 `#f0f4fa`，左侧 3px 深蓝条
- **股票池**：深蓝表头，隔行浅灰条纹，左对齐投资逻辑
- **Footer**：深蓝底 `#1a365d`，浅灰白字 `#d0d8e0`，两行简洁
- **全局字体大小**：
  - 一级标题 1.1em
  - 二级标题 1em
  - 事件卡片/热点/观点正文 0.88em
  - 标签（"事件""分析"等）0.88em 加粗
  - 表格 0.82em
  - Footer 0.78em
  - 市场总览价格 0.85em/0.75em
  - 禁止 `.bx` 单独设 0.9em 覆盖全局

CSS 核心框架：

```css
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,'PingFang SC','Microsoft YaHei','Helvetica Neue',sans-serif;font-size:15px;line-height:1.7;color:#1a1a2e;background:#f5f6fa;padding:0}
.c{max-width:640px;margin:0 auto;background:#fff}
.header{background:linear-gradient(135deg,#1a365d 0%,#2d5a87 100%);color:#fff;padding:28px 20px 20px;text-align:center}
.header h1{font-size:1.3em;font-weight:700;letter-spacing:1px;margin-bottom:4px}
.header .date{font-size:0.85em;opacity:0.8}

.s{padding:20px;border-bottom:6px solid #f0f2f7}
.stt{font-size:1.1em;font-weight:700;color:#1a365d;padding-bottom:10px;margin-bottom:14px;border-bottom:2px solid #1a365d}
.sh{font-size:1em;font-weight:600;color:#2d5a87;margin:16px 0 8px;padding-left:10px;border-left:3px solid #2d5a87}

/* 3×3 grid */
.grid3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;margin-bottom:8px}
.g3-cell{text-align:center;padding:6px;border-radius:4px;background:#f8fafc;border:1px solid #e5e7eb}
.g3-cell .name{font-size:0.78em;color:#64748b;margin-bottom:2px}
.g3-cell .price{font-size:0.85em;font-weight:600;color:#1a1a2e}
.g3-cell .chg{font-size:0.75em;font-weight:600}
.g3-cell .up{color:#c41e3a}
.g3-cell .dn{color:#16a34a}

.mt-bar{padding:10px 14px;margin:6px 0 0;font-size:0.88em;color:#475569;background:#f8fafc;border-radius:6px;border:1px solid #e5e7eb;line-height:1.7}

.bx{margin:10px 0;padding:12px 14px;border-radius:6px;background:#f8fafc;border:1px solid #e5e7eb}
.bx .item-label{font-size:0.88em;font-weight:700;color:#1a365d;margin-bottom:4px}
.bx p{font-size:0.88em;color:#475569;line-height:1.7}

.feature-block{margin:12px 0;padding:14px 16px;background:#f8fafc;border-radius:6px;border:1px solid #e5e7eb}
.feature-block h4{font-size:0.95em;font-weight:700;color:#1a365d;margin-bottom:8px}
.feature-block p{font-size:0.88em;color:#475569;line-height:1.7}

.chief-block{margin:12px 0;padding:14px 16px;background:#f0f4fa;border-radius:6px;border-left:3px solid #2d5a87}
.chief-block h4{font-size:0.95em;font-weight:700;color:#1a365d;margin-bottom:8px}
.chief-block p{font-size:0.88em;color:#475569;line-height:1.7}

.tb{overflow-x:auto;margin:8px 0 12px}
table{width:100%;border-collapse:collapse;font-size:0.82em;min-width:280px}
th{background:#1a365d;color:#fff;padding:7px 8px;text-align:center;font-weight:600}
td{padding:7px 8px;text-align:center;border-bottom:1px solid #e5e7eb}
tr:nth-child(even) td{background:#f8fafc}

.ft{background:#1a365d;color:#d0d8e0;padding:16px 20px;font-size:0.78em;text-align:center;line-height:1.6}
.ft p{color:#d0d8e0;margin:2px 0}
```

---

## 数据验证清单（写入前必查）

每个报告中的数据都必须经过以下验证：

### 指数点位验证

- [ ] A股指数：Gangtise `quote.py` + KB（每日晨报/晨会纪要）+ 财联社新闻，**三源交叉验证**
- [ ] 港股指数：Gangtise `quote.py` + KB（证券早晨快讯/港股点评）+ 财联社新闻，**三源交叉验证**
- [ ] 美股指数：Gangtise EDB（M00006167/M00009828/M00009829）+ KB + 财联社，**三源交叉验证**
- [ ] 所有指数收盘价：先拉取主力源数据，再用KB检索同一日报告中的收盘数据比对，偏差>0.5%需排查原因

### 数据格式验证

- [ ] 已公布数据直接写入，未公布数据写预期+公布日期
- [ ] 涨跌幅统一「+x% / -x%」格式
- [ ] 禁止出现终端品牌名（Wind/同花顺/东方财富等）
- [ ] 禁止补丁痕迹（尚未公布/修正/补正/更新为/待确认）
- [ ] 每个事件和数字必须有可追溯的数据来源

### 内容验证

- [ ] 宏观要紧扣当周，禁止跨周跨月旧闻
- [ ] 每条热点必须附带分析（产业链传导/预期差/持续性判断）
- [ ] 首席观点隐去分析师姓名和报告标题
- [ ] 股票池赛道细分，最多10只
- [ ] 港股美股指数数据：KB检索不到时用web_search财联社新闻补充
- [ ] 每条产业要闻：走KB检索 + 财联社方向验证

---

## 注意事项

- 标题固定为「**二级市场早报**」，居中，不出现其他名称。
- 日期格式：`{YYYY}年{M}月{D}日（周{X}）| 数据截至{M-1}月{D-1}日收盘`
- **禁止**出现券商/数据终端品牌名，数据来源统一写"Gangtise 数据终端"
- **禁止**编造事件或数字
- **禁止**写"建议买入/卖出"等投资建议
- **禁止**出现非当周或前日的旧闻
- 某板块不足 3 条，就写 1-2 条，不凑数
- 热点话题深度 ≥5 条
- 首席观点精选 ≥5 条（隐去分析师姓名和报告标题）
- 股票池最多 10 只，赛道细分命名
- 所有数据优先使用 Gangtise 终端拉取
- 宏观要闻和产业要闻：KB检索后必须用财联社/金十新闻方向性核验
- 恒生科技/标普500数据需重点核验，这两指数容易出现数据偏差
