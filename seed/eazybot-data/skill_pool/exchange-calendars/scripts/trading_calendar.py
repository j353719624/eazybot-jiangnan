#!/usr/bin/env python3
"""全球交易日历查询工具，基于 exchange_calendars 库。"""

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import exchange_calendars as ec


# ── 中文别名 → 交易所代码 ──────────────────────────────────────
# 覆盖全部 102 个交易所，按地区分组

ALIASES = {
    # 中国
    "A股": "XSHG", "上证": "XSHG", "沪市": "XSHG", "上交所": "XSHG",
    "深证": "XSHG", "深市": "XSHG", "深交所": "XSHG",
    "港股": "XHKG", "港交所": "XHKG", "香港": "XHKG",
    "台股": "XTAI", "台湾": "XTAI",

    # 美国
    "美股": "XNYS", "纽交所": "XNYS", "纽约证券交易所": "XNYS",
    "纳斯达克": "XNAS",
    "美交所": "XASE", "AMEX": "XASE",
    "BATS": "BATS",
    "OTC": "OOTC",
    "美国期货": "us_futures",
    "CBOT": "CBOT", "芝加哥商品": "CME", "CME": "CME",
    "COMEX": "COMEX", "NYMEX": "NYMEX",
    "CFE": "CFE", "CMES": "CMES", "ICEUS": "ICEUS",

    # 日本
    "日股": "XTKS", "东证": "XTKS", "日本": "XTKS", "东京": "XTKS", "JPX": "JPX",

    # 韩国
    "韩股": "XKRX", "韩国": "XKRX",

    # 东南亚
    "新加坡": "XSES",
    "印尼": "XIDX", "雅加达": "JKT",
    "泰国": "XBKK", "曼谷": "XBKK",
    "菲律宾": "XPHS", "马尼拉": "XPHS",
    "马来西亚": "XKLS", "吉隆坡": "XKLS",
    "巴基斯坦": "XKAR", "卡拉奇": "XKAR",

    # 印度
    "印度": "XBOM", "孟买": "XBOM", "BSE": "BSE",

    # 中东
    "以色列": "TASE", "特拉维夫": "TASE",
    "沙特": "XSAU", "利雅得": "XSAU",
    "哈萨克斯坦": "AIXK",

    # 欧洲西
    "英股": "XLON", "伦敦": "XLON",
    "爱尔兰": "XDUB", "都柏林": "XDUB",
    "法股": "XPAR", "巴黎": "XPAR",
    "德股": "XETR", "德国": "XETR", "法兰克福": "XFRA",
    "瑞士": "XSWX", "苏黎世": "XSWX", "SIX": "SIX",
    "荷兰": "XAMS", "阿姆斯特丹": "XAMS",
    "比利时": "XBRU", "布鲁塞尔": "XBRU",
    "卢森堡": "XLUX",

    # 欧洲北
    "瑞典": "XSTO", "斯德哥尔摩": "XSTO",
    "芬兰": "XHEL", "赫尔辛基": "XHEL",
    "丹麦": "XCSE", "哥本哈根": "XCSE",
    "挪威": "XOSE", "奥斯陆": "OSE",
    "冰岛": "XICE", "雷克雅未克": "XICE",
    "新西兰": "XNZE",

    # 欧洲东 & 中
    "波兰": "XWAR", "华沙": "XWAR",
    "捷克": "XPRA", "布拉格": "XPRA",
    "匈牙利": "XBUD", "布达佩斯": "XBUD",
    "奥地利": "XWBO", "维也纳": "XWBO",
    "希腊": "ASEX", "雅典": "ASEX",
    "土耳其": "XIST", "伊斯坦布尔": "XIST",
    "俄罗斯": "XMOS", "莫斯科": "XMOS",
    "克罗地亚": "XZAG", "萨格勒布": "XZAG",
    "斯洛文尼亚": "XLJU",
    "斯洛伐克": "XBRA", "布拉迪斯拉发": "XBRA",
    "立陶宛": "XLIT", "维尔纽斯": "XLIT",
    "爱沙尼亚": "XTAL", "塔林": "XTAL",
    "拉脱维亚": "XRIS", "里加": "XRIS",
    "塞尔维亚": "XBEL", "贝尔格莱德": "XBEL",
    "罗马尼亚": "XBSE", "布加勒斯特": "XBSE",
    "百慕大": "XBDA",
    "塞浦路斯": "XCYS",
    "意大利": "XMIL", "米兰": "XMIL",
    "西班牙": "XMAD", "马德里": "XMAD",
    "葡萄牙": "XLIS", "里斯本": "XLIS",

    # 拉美
    "巴西": "BVMF", "圣保罗": "BVMF", "BMF": "BMF",
    "墨西哥": "XMEX", "墨西哥城": "XMEX",
    "阿根廷": "XBUE", "布宜诺斯艾利斯": "XBUE",
    "智利": "XSGO", "圣地亚哥": "XSGO",
    "秘鲁": "XLIM", "利马": "XLIM",
    "哥伦比亚": "XBOG",

    # 加拿大
    "加拿大": "XTSE", "多伦多": "XTSE", "TSX": "TSX", "多伦多创业板": "XTSX",

    # 澳洲 & 非洲
    "澳洲": "XASX", "澳大利亚": "XASX", "悉尼": "XASX",
    "南非": "XJSE", "约翰内斯堡": "XJSE",

    # 其他
    "24/5": "24/5", "24/7": "24/7",
    "ICE": "ICE", "IEPA": "IEPA", "NYFE": "NYFE",
    "FWB": "FWB", "LSE": "LSE", "HKEX": "HKEX",
    "BVB": "BVB", "TASE": "TASE",
    "XEUR": "XEUR", "XEEE": "XEEE", "XSTU": "XSTU", "XHAM": "XHAM",
    "XDUS": "XDUS", "XTAE": "XTAE", "XCBF": "XCBF",
}

# snapshot 默认查询的市场
SNAPSHOT_DEFAULTS = ["A股", "港股", "美股", "纳斯达克", "日股", "韩股", "英股", "德国", "台股"]

# 用户友好的市场名
FRIENDLY_NAMES = {
    "XSHG": "A股", "XHKG": "港股", "XNYS": "美股(纽交所)", "XNAS": "美股(纳斯达克)",
    "XTKS": "日股(东证)", "XKRX": "韩股", "XLON": "英股(伦敦)", "XETR": "德股",
    "XPAR": "法股", "XBOM": "印股(孟买)", "XASX": "澳股", "XTAI": "台股",
    "XSES": "新加坡", "BVMF": "巴西", "XTSE": "加拿大",
    "SSE": "A股(上交所)", "HKEX": "港股", "NYSE": "美股(纽交所)", "NASDAQ": "美股(纳斯达克)",
    "JPX": "日股(JPX)", "LSE": "英股(LSE)", "TSX": "加拿大(TSX)",
    "ASX": "澳股(ASX)", "BSE": "印股(BSE)",
    "XSWX": "瑞士", "XAMS": "荷兰", "XBRU": "比利时", "XIST": "土耳其",
    "XMIL": "意大利", "XMAD": "西班牙", "XWAR": "波兰", "XSTO": "瑞典",
    "XHEL": "芬兰", "XCSE": "丹麦", "OSE": "挪威", "XICE": "冰岛",
    "XKLS": "马来西亚", "XBKK": "泰国", "XPHS": "菲律宾", "XIDX": "印尼",
    "XSAU": "沙特", "TASE": "以色列", "XJSE": "南非",
    "XMEX": "墨西哥", "XSGO": "智利", "XBUE": "阿根廷",
    "XBDA": "百慕大",
}


def _schedule_row(cal, day):
    """取某日 schedule 行，索引时区与 schedule.index 对齐。"""
    idx = pd.Timestamp(day)
    index_tz = cal.schedule.index.tz
    if index_tz is not None:
        if idx.tzinfo is None:
            idx = idx.tz_localize(index_tz)
        else:
            idx = idx.tz_convert(index_tz)
    return cal.schedule.loc[idx]


def resolve_exchange(name: str) -> str:
    """解析交易所代码，支持别名。"""
    upper = name.upper().strip()
    if upper in ALIASES:
        return ALIASES[upper]
    if name.strip() in ALIASES:
        return ALIASES[name.strip()]
    all_names = ec.get_calendar_names()
    if upper in all_names:
        return upper
    raise ValueError(f"未知交易所: {name}。支持别名: {', '.join(ALIASES.keys())}")


def is_trading_day(exchange: str, target_date: str) -> dict:
    """判断某天是否为交易日。"""
    code = resolve_exchange(exchange)
    cal = ec.get_calendar(code)
    td = date.fromisoformat(target_date)
    is_session = cal.is_session(td)

    result = {
        "exchange": code,
        "date": target_date,
        "is_trading_day": is_session,
    }

    if is_session:
        try:
            sched = _schedule_row(cal, td)
            tz = str(cal.tz)
            result["market_open"] = sched["open"].tz_convert(tz).strftime("%H:%M")
            result["market_close"] = sched["close"].tz_convert(tz).strftime("%H:%M")
            bs = sched.get("break_start")
            be = sched.get("break_end")
            if bs is not None and str(bs) != "NaT":
                result["break_start"] = bs.tz_convert(tz).strftime("%H:%M")
                result["break_end"] = be.tz_convert(tz).strftime("%H:%M")
            result["timezone"] = tz
        except (KeyError, TypeError):
            pass

    return result


def next_trading_day(exchange: str, target_date: str, n: int = 1) -> dict:
    """查询未来第 n 个交易日。"""
    code = resolve_exchange(exchange)
    cal = ec.get_calendar(code)
    d = date.fromisoformat(target_date)
    last = cal.last_session.date()
    search_end = min(d + timedelta(days=365), last)
    sessions = cal.sessions_in_range(d + timedelta(days=1), search_end)
    if len(sessions) >= n:
        target = sessions[n - 1]
        return {"exchange": code, "date": str(target.date()), "offset": n}
    return {"exchange": code, "error": f"在一年内找不到第 {n} 个交易日"}


def trading_days_range(exchange: str, start: str, end: str) -> dict:
    """查询日期范围内的交易日列表。"""
    code = resolve_exchange(exchange)
    cal = ec.get_calendar(code)
    sessions = cal.sessions_in_range(start, end)
    return {
        "exchange": code,
        "start": start,
        "end": end,
        "total": len(sessions),
        "dates": [str(s.date()) for s in sessions],
    }


def list_exchanges() -> list:
    """列出所有支持的交易所。"""
    all_names = sorted(ec.get_calendar_names())
    result = []
    for name in all_names:
        try:
            cal = ec.get_calendar(name)
            friendly = FRIENDLY_NAMES.get(name, "")
            result.append({
                "code": name,
                "name": friendly,
                "timezone": str(cal.tz),
                "bound_start": str(cal.first_session.date()),
                "bound_end": str(cal.last_session.date()),
            })
        except Exception:
            result.append({"code": name})
    return result


def holidays(exchange: str, year_or_month: str) -> dict:
    """查询某年或某月的节假日（工作日休市日）。"""
    code = resolve_exchange(exchange)
    cal = ec.get_calendar(code)
    friendly = FRIENDLY_NAMES.get(code, code)

    # 解析参数：YYYY 或 YYYY-MM
    if len(year_or_month) == 4:
        start = date(int(year_or_month), 1, 1)
        end = date(int(year_or_month), 12, 31)
    elif len(year_or_month) == 7:
        y, m = year_or_month.split("-")
        start = date(int(y), int(m), 1)
        # 月末
        if int(m) == 12:
            end = date(int(y), 12, 31)
        else:
            end = date(int(y), int(m) + 1, 1) - timedelta(days=1)
    else:
        return {"error": "参数格式应为 YYYY 或 YYYY-MM"}

    # 检查是否在日历范围内
    cal_start = cal.first_session.date()
    cal_end = cal.last_session.date()
    actual_start = max(start, cal_start)
    actual_end = min(end, cal_end)

    if actual_start > actual_end:
        return {
            "exchange": code, "market": friendly,
            "period": year_or_month,
            "holidays": [],
            "total": 0,
            "note": f"超出日历范围({cal_start}~{cal_end})",
        }

    # 工作日但非交易日 = 节假日
    d = actual_start
    hols = []
    while d <= actual_end:
        if d.weekday() < 5 and not cal.is_session(d):
            hols.append({"date": str(d), "weekday": d.strftime("%A")})
        d += timedelta(days=1)

    return {
        "exchange": code,
        "market": friendly,
        "period": year_or_month,
        "holidays": hols,
        "total": len(hols),
    }


def market_snapshot(target_datetime: str, markets: list | None = None) -> dict:
    """查询指定时刻全球主要市场的状态。"""
    if markets is None:
        markets = SNAPSHOT_DEFAULTS

    bj_tz = ZoneInfo("Asia/Shanghai")
    target_dt = datetime.strptime(target_datetime, "%Y-%m-%d %H:%M").replace(tzinfo=bj_tz)
    target_date = target_dt.date()

    results = []
    for alias in markets:
        try:
            code = resolve_exchange(alias)
            cal = ec.get_calendar(code)
            tz_str = str(cal.tz)
            friendly = FRIENDLY_NAMES.get(code, code)

            if target_date < cal.first_session.date() or target_date > cal.last_session.date():
                results.append({
                    "market": friendly, "exchange": code,
                    "date": str(target_date),
                    "is_trading_day": None, "status": "超出日历范围",
                    "timezone": tz_str,
                })
                continue

            is_session = cal.is_session(target_date)

            if not is_session:
                last = cal.last_session.date()
                search_end = min(target_date + timedelta(days=30), last)
                future = cal.sessions_in_range(target_date + timedelta(days=1), search_end)
                next_session = str(future[0].date()) if len(future) > 0 else None
                results.append({
                    "market": friendly, "exchange": code,
                    "date": str(target_date),
                    "is_trading_day": False, "status": "休市",
                    "next_trading_day": next_session,
                    "timezone": tz_str,
                })
                continue

            sched = _schedule_row(cal, target_date)
            open_local = sched["open"].tz_convert(tz_str)
            close_local = sched["close"].tz_convert(tz_str)
            open_bj = sched["open"].tz_convert("Asia/Shanghai")
            close_bj = sched["close"].tz_convert("Asia/Shanghai")

            entry = {
                "market": friendly, "exchange": code,
                "date": str(target_date),
                "is_trading_day": True,
                "timezone": tz_str,
                "local_open": open_local.strftime("%H:%M"),
                "local_close": close_local.strftime("%H:%M"),
                "bj_open": open_bj.strftime("%H:%M"),
                "bj_close": close_bj.strftime("%H:%M"),
            }

            bs = sched.get("break_start")
            be = sched.get("break_end")
            if bs is not None and str(bs) != "NaT":
                entry["local_break"] = f"{bs.tz_convert(tz_str).strftime('%H:%M')}-{be.tz_convert(tz_str).strftime('%H:%M')}"
                entry["bj_break"] = f"{bs.tz_convert('Asia/Shanghai').strftime('%H:%M')}-{be.tz_convert('Asia/Shanghai').strftime('%H:%M')}"

            target_bj = target_dt
            if target_bj < open_bj:
                entry["status"] = "未开盘"
            elif target_bj >= close_bj:
                entry["status"] = "已收盘"
            else:
                if "bj_break" in entry:
                    break_start_str, break_end_str = entry["bj_break"].split("-")
                    break_start_dt = open_bj.replace(
                        hour=int(break_start_str.split(":")[0]),
                        minute=int(break_start_str.split(":")[1]),
                    )
                    break_end_dt = open_bj.replace(
                        hour=int(break_end_str.split(":")[0]),
                        minute=int(break_end_str.split(":")[1]),
                    )
                    if break_start_dt <= target_bj < break_end_dt:
                        entry["status"] = "午休中"
                    else:
                        entry["status"] = "交易中"
                else:
                    entry["status"] = "交易中"

            results.append(entry)
        except Exception as e:
            results.append({"market": alias, "error": str(e)})

    return {"query_time_bj": target_datetime, "markets": results}


def main():
    parser = argparse.ArgumentParser(description="全球交易日历查询")
    sub = parser.add_subparsers(dest="command")

    p_open = sub.add_parser("is_open", help="判断某天是否为交易日")
    p_open.add_argument("exchange", help="交易所代码或别名")
    p_open.add_argument("date", help="日期 YYYY-MM-DD，默认今天", nargs="?", default=date.today().isoformat())

    p_next = sub.add_parser("next", help="查询未来第 n 个交易日")
    p_next.add_argument("exchange", help="交易所代码或别名")
    p_next.add_argument("date", help="起始日期 YYYY-MM-DD", nargs="?", default=date.today().isoformat())
    p_next.add_argument("-n", type=int, default=1, help="第 n 个交易日，默认 1")

    p_range = sub.add_parser("range", help="查询日期范围内的交易日")
    p_range.add_argument("exchange", help="交易所代码或别名")
    p_range.add_argument("start", help="开始日期 YYYY-MM-DD")
    p_range.add_argument("end", help="结束日期 YYYY-MM-DD")

    sub.add_parser("list", help="列出所有支持的交易所")

    p_hol = sub.add_parser("holidays", help="查询某年或某月的节假日")
    p_hol.add_argument("exchange", help="交易所代码或别名")
    p_hol.add_argument("year_or_month", help="年份 YYYY 或月份 YYYY-MM")

    p_snap = sub.add_parser("snapshot", help="查询指定时刻全球主要市场状态")
    p_snap.add_argument("datetime", help="日期时间 YYYY-MM-DD HH:MM，视为北京时间")
    p_snap.add_argument("-m", "--markets", nargs="+", help="市场别名列表，默认主要市场")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "is_open":
            print(json.dumps(is_trading_day(args.exchange, args.date), ensure_ascii=False, indent=2))
        elif args.command == "next":
            print(json.dumps(next_trading_day(args.exchange, args.date, args.n), ensure_ascii=False, indent=2))
        elif args.command == "range":
            print(json.dumps(trading_days_range(args.exchange, args.start, args.end), ensure_ascii=False, indent=2))
        elif args.command == "list":
            print(json.dumps(list_exchanges(), ensure_ascii=False, indent=2))
        elif args.command == "holidays":
            print(json.dumps(holidays(args.exchange, args.year_or_month), ensure_ascii=False, indent=2))
        elif args.command == "snapshot":
            mkts = args.markets if args.markets else None
            print(json.dumps(market_snapshot(args.datetime, mkts), ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
