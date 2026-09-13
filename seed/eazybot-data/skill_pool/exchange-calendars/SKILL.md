---
name: exchange-calendars
description: 全球交易日历查询，支持 102 个交易所的交易日判断、节假日查询、时刻快照（未开盘/交易中/午休/已收盘/休市）。当用户询问某市场（A股、港股、美股、日股、韩股、英股等）某天是否开市、某时刻全球市场状态、节假日休市安排、未来交易日时触发。补充 stock-sdk-mcp 仅支持 A 股交易日历的不足。
metadata:
  builtin_skill_version: "1.0"
---

# 全球交易日历

基于 `exchange_calendars` 库，查询全球 102 个交易所的交易日历。

## 用法

所有查询通过脚本执行：

```bash
python3 scripts/trading_calendar.py <command> <args>
```

**必须在 skill 目录下执行**（`cd` 到 SKILL.md 所在目录）。

### 全球市场快照（推荐）

查询指定北京时间时刻，全球主要市场状态及开收盘时间：

```bash
python3 scripts/trading_calendar.py snapshot "2026-06-04 09:00"
python3 scripts/trading_calendar.py snapshot "2026-06-04 14:00" -m A股 港股 美股
```

返回各市场 `status`：未开盘 / 交易中 / 午休中 / 已收盘 / 休市

### 查询节假日

列出某年或某月的工作日休市日：

```bash
# 某年
python3 scripts/trading_calendar.py holidays A股 2026
python3 scripts/trading_calendar.py holidays 美股 2026
# 某月
python3 scripts/trading_calendar.py holidays 韩股 2026-06
```

### 判断是否交易日

```bash
python3 scripts/trading_calendar.py is_open A股 2026-06-04
python3 scripts/trading_calendar.py is_open 美股
```

### 查询未来交易日

```bash
python3 scripts/trading_calendar.py next A股 2026-06-04 -n 3
```

### 查询日期范围内的交易日

```bash
python3 scripts/trading_calendar.py range 日股 2026-06-01 2026-06-30
```

### 列出所有支持的交易所

```bash
python3 scripts/trading_calendar.py list
```

## 中文别名

查询时可直接用中文别名，无需记代码：A股、港股、美股、纳斯达克、日股、韩股、英股、德股、法股、印度、澳洲、台股、新加坡、巴西、加拿大、以色列、沙特、泰国、印尼、马来西亚、菲律宾、波兰、捷克、匈牙利、土耳其、俄罗斯等。完整列表见 [references/exchanges.md](references/exchanges.md)。

## 参考文档

- [支持的交易所及别名](references/exchanges.md)
