---
name: gangtise-market-review
description: "生成每日 A 股市场全景收盘复盘。整合 Gangtise 投研数据——热点话题、行情、首席观点、投研线索、行业指标(EDB)——产出8大模块结构化复盘报告。 输出 Markdown + 米黄色晚报风格 HTML（衬线标题 + 报刊排版）。"
version: 1.3.2
author: Gangtise
metadata:
  builtin_skill_version: "1.0"
  category: research
  latestVersionUrl: "https://gts-download.obs.cn-east-3.myhuaweicloud.com/skills/gangtise-market-review.zip"
  related_skills:
    - gangtise-agent
    - gangtise-data
    - gangtise-file
---

# A股市场全景复盘 v2.2

## 概览

本工具通过整合 Gangtise 投研数据，生成每日 A 股市场全景收盘复盘报告。采用 **Evening Post（晚报）** 设计系统，**双层数据架构**（全市场共性层 + 热点深度层）。

**设计风格：晚报风**
- 米黄色背景 `#F7F3E9`，深墨色文字 `#1C1917`
- 强调色：赭褐 `#92400E`（标题/分级）
- 字体：Noto Serif SC（衬线标题）+ Noto Sans SC（无衬线正文）
- 涨跌幅：红涨 `#B91C1C` 绿跌 `#15803D`（A股标准）
- 报头：双线分隔 + 刊头大字 + 日期版次
- 正文：首行缩进、两端对齐、段落分明

**数据架构：双层数据**

| 层级 | 数据范围 | 用途 | 数据源 |
|:-----|:---------|:-----|:-------|
| **共性层** | 全市场A股截面数据（~5200只） | 01大盘速览、02资金结构TOP10、03强弱势TOP10 | `quote.py --all-market --type snap` |
| **热点层** | 热点关联证券池（30~100只） | 04热点拆解（产业链深度分析） | `hot_topic.py` 提取 + `quote.py` 批量查询 |
| **观点层** | 首席观点/研报/纪要 | 05机构声音 | `gangtise-file/opinion.py` / `report.py` / `summary.py` |

**核心原则：**
- 02资金结构、03强弱势使用全市场共性层数据
- 04热点拆解使用热点层数据
- 排序逻辑需标注：每份TOP表格注明排序方式（如"按成交额排序，全市场A股"）
- 05机构声音从 `gangtise-file` 检索，不引用早报观点
- 06事件驱动中的个股涨跌映射到具体催化事件

### 报告模块（8大模块）

| 模块 | 内容 | 数据源 | 数据层级 |
|:-----|:-----|:-------|:---------|
| 01 今日大盘速览 | 8大指数 + 量能 + 核心判断 + 4条观察 | `quote.py`（指数） | 共性层 |
| 02 资金结构 | 全市场成交额TOP10 + 集中度分析 | `quote.py --all-market --type snap` | 共性层 |
| 03 强势与弱势 | 全市场涨幅TOP10 + 跌幅TOP10 + 轮动逻辑 | `quote.py --all-market --type snap` | 共性层 |
| 04 热点拆解 | 按当日热点自然组织，催化→标的→产业链 | `hot_topic.py` + `concept.py` + `security_clue.py` | 热点层 |
| 05 机构声音 | 精选机构观点（首席+研报+纪要），从file检索 | `gangtise-file/opinion.py` + `report.py` + `summary.py` | 观点层 |
| 06 事件驱动 | 当日重大事件/政策 + 传导分析 | `hot_topic.py` + `industry_indicator.py` | — |
| 07 风险扫描 | 多维度风险 + 跟踪指标 + 应对 | `quote.py` + `valuation.py` | — |
| 08 明日展望 | 2-3个情景，以"若..."条件句触发 | 综合分析 | — |

---

## 依赖技能与脚本

| 技能 | 用途 | 脚本 | 使用时机 |
|:-----|:-----|:-----|:---------|
| `gangtise-agent` | 热点话题列表（全天早报/午报/盘中/晚报） | `scripts/hot_topic.py` | 每次必用 |
| `gangtise-data` | 指数行情 + 全市场截面行情 | `scripts/quote.py` | 每次必用 |
| `gangtise-data` | 题材指数投资逻辑 + 成分股 | `scripts/concept.py` | 热点拆解时 |
| `gangtise-data` | 估值分析 | `scripts/valuation.py` | 风险扫描（估值拥挤度） |
| `gangtise-data` | 行业指标 EDB | `scripts/industry_indicator.py` | 事件驱动（宏观数据） |
| `gangtise-agent` | 投研线索 | `scripts/security_clue.py` | 热点拆解（个股归因） |
| `gangtise-file` | 首席观点 | `scripts/opinion.py` | 机构声音模块 |
| `gangtise-file` | 研究报告 | `scripts/report.py` | 机构声音模块（研报） |
| `gangtise-file` | 会议纪要 | `scripts/summary.py` | 机构声音模块（纪要） |

---

## Step 1: 拉取热点话题（全天覆盖）

```bash
python3 skills/gangtise-agent/scripts/hot_topic.py \
  --page-size 30 \
  -sd {YYYY-MM-DD} \
  -ed {YYYY-MM-DD} \
  --hot-category "morningBriefing,noonBriefing,intradayBriefing,eveningBriefing" \
  --with-securities \
  --with-close-reading
```

提取所有 `securities` 字段构建热点证券池（30~100只），用于 04 热点拆解。

---

## Step 2: 拉取行情数据（双层数据）

### 2.1 共性层：全市场A股截面数据

使用 `--all-market --type snap` 获取当日全市场所有A股的收盘价、涨跌幅、成交额：

```bash
python3 skills/gangtise-data/scripts/quote.py \
  --all-market \
  --type snap \
  -sd {YYYY-MM-DD} \
  -ed {YYYY-MM-DD} \
  --limit 10000
```

返回数据包含约5200只A股（SH/SZ/BJ）的截面行情，字段包括：`最新价`、`涨跌幅`、`成交额`、`成交量` 等。

> `--all-market --type snap` 始终返回最近交易日的截面数据，`trade_date` 字段为实际数据日期。后续所有脚本统一使用该 `trade_date`，避免日期不一致。

**处理步骤：**
1. 读取 CSV，过滤 `交易所` 为 `SZ`/`SH`/`BJ` 的行
2. 去掉 `涨跌幅` 或 `成交额` 为空的停牌股
3. 按成交额从高到低排序 → 取前10 → 用于 02 资金结构
4. 按涨跌幅从高到低排序 → 取前10 → 用于 03 强势方向
5. 按涨跌幅从低到高排序 → 取前10 → 用于 03 弱势方向

> snap 数据不含 `security_abbr` 字段，仅返回 `security_code`。获取名称的方法：① 对 TOP 股票调用 `quote.py --securities`（日K接口），输出 HTML 注释中会显示代码→名称映射；② 调用 `security_clue.py --securities` 查询投研线索，返回结果自带名称。若名称缺失，用代码代替并标注。

### 2.2 指数行情（8大指数）

```bash
python3 skills/gangtise-data/scripts/quote.py \
  --securities "上证指数,深证成指,创业板指,科创50,北证50,上证50,沪深300,中证500" \
  -sd {YYYY-MM-DD} \
  -ed {YYYY-MM-DD}
```

日期与 snap 数据的 `trade_date` 一致。周一复盘时 snap 返回周一数据，指数行情也用周一日期。

### 2.3 热点层：热点证券池行情（用于热点拆解）

从 Step 1 的热点话题中提取所有涉及的证券，构建证券池，批量查询行情：

```bash
python3 skills/gangtise-data/scripts/quote.py \
  --securities "证券A,证券B,证券C,..." \
  -sd {YYYY-MM-DD} \
  -ed {YYYY-MM-DD}
```

热点层仅用于 04 热点拆解模块。02 资金结构和 03 强弱势使用 2.1 的共性层数据。

---

## Step 3: 扩展数据拉取（按需，增强深度）

### 3.1 机构声音（从 file 检索）

通过以下脚本检索真实机构观点，不引用早报中的观点摘要：

```bash
# 首席观点检索
python3 skills/gangtise-file/scripts/opinion.py \
  -k "AI芯片 半导体" \
  -sd {YYYY-MM-DD} \
  -ed {YYYY-MM-DD} \
  -l 10

# 研究报告检索
python3 skills/gangtise-file/scripts/report.py \
  -k "光模块 NPO" \
  -sd {YYYY-MM-DD} \
  -ed {YYYY-MM-DD} \
  -l 10

# 会议纪要检索
python3 skills/gangtise-file/scripts/summary.py \
  -k "智能驾驶 自动驾驶" \
  -sd {YYYY-MM-DD} \
  -ed {YYYY-MM-DD} \
  -l 10
```

用当日热点关键词搜索，每个关键词取3-5条最相关观点。

### 3.2 题材指数（热点拆解）

```bash
python3 skills/gangtise-data/scripts/concept.py \
  -n "题材名称" \
  --type all
```

### 3.3 投研线索（个股归因）

```bash
python3 skills/gangtise-agent/scripts/security_clue.py \
  --page-from 0 \
  --page-size 20 \
  -st "{YYYY-MM-DD} 00:00:00" \
  -et "{YYYY-MM-DD} 23:59:59" \
  -q bySecurity \
  --securities "标的A,标的B,..." \
  --source researchReport,conference,view
```

### 3.4 估值分析（风险扫描，可选）

```bash
python3 skills/gangtise-data/scripts/valuation.py \
  --securities "标的A,标的B,..." \
  -sd {YYYY-MM-DD} \
  -ed {YYYY-MM-DD}
```

### 3.5 行业指标 EDB（事件驱动，可选）

```bash
python3 skills/gangtise-data/scripts/industry_indicator.py \
  -m combine \
  -k "[宏观指标关键词]" \
  -sd {YYYY-MM-DD-30} \
  -ed {YYYY-MM-DD} \
  -l 5
```

---

## Step 4: 数据排序与标注

### 4.1 资金结构（全市场成交额TOP10）

1. 从共性层 snap 数据中提取所有A股的 `成交额` 字段
2. 按成交额从高到低排序
3. 取前10名
4. 表格表头标注："按成交额排序，全市场A股"
5. 结构判断：分析资金集中度、新旧主线切换、高位股与低位股表现

### 4.2 强势与弱势（全市场涨幅TOP10 / 跌幅TOP10）

1. 从共性层 snap 数据中提取所有A股的 `涨跌幅` 字段
2. 涨幅TOP10：按涨跌幅从高到低排序，取前10名
3. 跌幅TOP10：按涨跌幅从低到高排序，取前10名
4. 表格表头标注："按涨跌幅排序，全市场A股"
5. 轮动逻辑：分析强势与弱势方向的对比，资金流向

### 4.3 排序数据标注规范

在 HTML 表格中标注排序逻辑：
- 表头行上方加注释：`注释：按成交额排序，全市场A股`
- 或表头列名：`标的（按成交额排序）`
- 或表格下方加说明文字

---

## Step 5: 撰写复盘报告（Markdown）

务必阅读 [references/template.md](references/template.md) 的结构模板。报告结构见模板，写作质量标准见 [references/writing-standards.md](references/writing-standards.md)。

### 关键写作原则

1. **双层数据，分模块使用**：02 资金结构、03 强弱势使用全市场 snap 数据；04 热点拆解使用热点证券池数据。两者不混用。

2. **排序数据标注**：TOP表格在表头或注释中标注排序逻辑（如"按成交额排序，全市场A股"）。

3. **机构声音来源**：使用 `gangtise-file` 的 `opinion.py` / `report.py` / `summary.py` 获取机构观点，不引用早报直接提取。

4. **归因链完整**：每只个股涨跌映射到具体催化事件（热点话题/投研线索/首席观点）。全市场TOP10中找不到归因的标的，可标注"催化待确认"或从投研线索补充。

5. **情景展望**：2-3 个情景，以"若..."条件句触发（如"若无重大变量，市场大概率延续...""若催化进一步发酵，市场有望...""若外部出现扰动，市场可能..."），不标注具体概率数字。

6. **热点自然组织**：根据当日热点自然结构组织，不预设固定数量（如"每天3条主线"）。

---

## Step 6: 生成 HTML

1. 内容骨架读 `references/template.md`；版式按下方「设计系统要点」手写 HTML（仓库无独立 `assets/template.html`）
2. 对照 Markdown 内容稿，逐项填入真实数据
3. 输出文件：`YYYY-MM-DD-市场复盘.html`（与 MD 同目录、同名）

### 设计系统要点

- **背景**：`#F7F3E9` 米黄色
- **文字**：`#1C1917` 深墨色（标题），`#44403C` 灰褐（正文）
- **强调色**：`#92400E` 赭褐
- **涨跌幅**：红涨 `#B91C1C` 绿跌 `#15803D`（A股标准）
- **字体**：Noto Serif SC（衬线标题）+ Noto Sans SC（无衬线正文）
- **报头**：双线分隔 + 刊头大字 + 日期版次
- **正文**：首行缩进 2em、两端对齐、段落分明
- **表格**：细线框格，表头浅米色背景，无斑马纹，每页表格标注排序逻辑
- **热点分级**：S/A/B/C 衬线字标签，黑底白字
- **机构声音**：来源标注（首席观点/研报/纪要），机构名（衬线字，赭褐色）+ 正文（无衬线）。仅标注机构名称，不保留分析师个人姓名。
- **风险扫描**：双列网格，边框卡片
- **情景展望**：边框卡片，标题（衬线）+ 情景定性标签（衬线，赭褐色）

---

## 交付说明

- 输出格式：Markdown + HTML，HTML 可直接在浏览器中查看
- 文件名：`YYYY-MM-DD-市场复盘.md` / `YYYY-MM-DD-市场复盘.html`

## 关键数据事实

1. **双层数据**：02 资金结构和 03 强弱势使用全市场 snap 数据；04 热点拆解使用热点证券池数据。
2. **排序标注**：TOP表格需标注排序逻辑和数据范围（如"按成交额排序，全市场A股"）。
3. **机构声音来源**：从 `gangtise-file` 检索（opinion.py / report.py / summary.py），不引用早报观点。
4. **数据真实性**：涨幅TOP10、跌幅TOP10、成交额TOP10 基于真实行情数据排序后取前N。
5. **日期格式**：文件名 `YYYY-MM-DD`，报告标题 `YYYY.MM.DD`。
6. **周末处理**：当 `{YYYY-MM-DD-1}` 为周末时，推算到最近交易日（周五）。
7. **归因映射**：个股涨跌映射到 Gangtise 热点话题/投研线索/首席观点里的具体催化事件。无归因的标的标注"催化待确认"。
8. **观点来源**：首席观点从 `gangtise-file` 获取，不使用 `gangtise-kb`。
9. **热点组织**：根据当日热点自然结构组织，不预设固定数量。
10. **证券名称映射**：snap 数据不含 `security_abbr`，仅返回 `security_code`。获取名称方法：① `quote.py --securities` 日K接口，HTML 注释中显示代码→名称映射；② `security_clue.py --securities` 查询投研线索，返回自带名称。缺失时用代码代替并标注。
11. **扩展数据按需**：基础复盘（Step 1+2）即可生成完整报告；"深度复盘"时启用 Step 3 扩展数据。
12. **日期对齐**：`--all-market --type snap` 返回最近交易日截面数据，不受 `-sd/-ed` 参数约束。先运行 snap 获取 `trade_date`，后续所有脚本统一使用该日期。周一复盘时 snap 返回周一数据。
13. **并行拉取**：Step 1（热点话题）、Step 2.1（全市场 snap）、Step 2.2（指数行情）、模板文件加载互不依赖，可并行发起。Step 2.3（热点证券池）需等 Step 1。Step 3.1（机构声音）关键词从 Step 1 热点提取。投研线索在获得 TOP 股票代码后并行拉取。
14. **标的格式**：涨幅榜、跌幅榜、成交额榜中每只股票同时包含名称和代码，格式为"博瑞医药（688166）"。snap 数据不含名称时按 note 10 方法补齐。
15. **标题分层**：核心判断标题（headline）过长时拆分为三层：①主标题（1行核心判断）、②副标题（1-2行行情说明）、③催化剂标签卡片（横向排列关键词标签）。标签卡片 CSS：`display:flex; gap:10px`，每个标签 `background: var(--paper-deep); border: 1px solid var(--border); padding: 4px 12px; border-radius: 4px; font-size: 12px`。
16. **CSS 涨跌颜色**：涨跌幅数值使用预定义 CSS 类名 `.up`（红涨 #B91C1C）和 `.down`（绿跌 #15803D），不使用内联 style 或自定义类名。模板已定义 `.up { color: var(--up) !important; }` 和 `.down { color: var(--down) !important; }`，确保全报告涨跌颜色统一。