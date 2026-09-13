#!/usr/bin/env python3
"""
自选股复盘 — 数据采集脚本 V2
从 Gangtise 各数据源拉取当日行情、资金流向、公告、研报线索、投研日程，
输出结构化 JSON 供主 Skill 编译日报。

用法:
    python3 scripts/collect_data.py --date 2026-07-22

输出:
    workspace/gangtise/portfolio_review/YYYY-MM-DD/
        ├── data.json          # 聚合后的结构化数据
        ├── QUOTES.csv         # 行情原始 CSV
        ├── FUND_FLOW.csv      # 资金流向原始 CSV (A股)
        ├── ANNOUNCEMENTS.md   # 公告
        ├── CLUES.md           # 投研线索
        ├── CALENDAR.md        # 投研日程
        └── ONE_LINE_SUMMARIES.md  # 一句话总结
"""

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
import urllib.error
from datetime import date, datetime, timedelta
from pathlib import Path

# ── 路径配置 ──
SKILL_DIR = Path(__file__).resolve().parent.parent
GANGTISE_DATA = SKILL_DIR.parent / "gangtise-data" / "scripts"
GANGTISE_FILE = SKILL_DIR.parent / "gangtise-file" / "scripts"
GANGTISE_AGENT = SKILL_DIR.parent / "gangtise-agent" / "scripts"
GANGTISE_PRIVATE = SKILL_DIR.parent / "gangtise-private" / "scripts"
WORKSPACE = SKILL_DIR.parent.parent / "workspace" / "gangtise" / "portfolio_review"


def run(cmd, cwd, timeout=90):
    """执行命令，返回 stdout/stderr 文本。"""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(cwd), timeout=timeout)
        if r.returncode != 0:
            print(f"[WARN] 返回码 {r.returncode}: {r.stderr[:400]}", file=sys.stderr)
        return r.stdout + r.stderr
    except subprocess.TimeoutExpired:
        print(f"[WARN] 超时 ({timeout}s): {' '.join(cmd[-4:])}", file=sys.stderr)
        return ""
    except Exception as e:
        print(f"[WARN] 异常: {e}", file=sys.stderr)
        return ""


def extract_csv_path(text, known_dir=None):
    """从脚本输出文本中提取 CSV 文件路径。
    
    策略：
    1. 找 `\`path/to/file.csv\`` 格式的包裹路径
    2. 找以 / 开头 .csv 结尾的行
    3. 如果 known_dir 指定，在该目录下找最新 .csv
    """
    # 策略1：找反引号包裹的路径
    m = re.search(r'`([^`]+\.csv)`', text)
    if m:
        p = Path(m.group(1))
        if p.exists():
            return p
    # 策略2：找以 / 开头 .csv 结尾的路径
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("/") and line.endswith(".csv"):
            # 去掉可能的后缀空白或字符
            p = Path(line.rstrip(".").rstrip())
            if p.exists():
                return p
    # 策略3：known_dir
    if known_dir:
        kd = Path(known_dir)
        if kd.exists():
            files = sorted(kd.glob("*.csv"))
            if files:
                return files[-1]
    return None


def write_securities_csv(stocks, tmp_path):
    """将自选股列表写入临时 CSV（只含 security_code 列）。"""
    tmp_path.parent.mkdir(parents=True, exist_ok=True)
    with open(tmp_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["security_code"])
        for s in stocks:
            w.writerow([s["code"]])


def get_stockpool():
    """获取当前用户所有自选股池的证券列表，返回 list[dict]."""
    script = GANGTISE_PRIVATE / "stockpool.py"
    run([sys.executable, str(script), "--all"], GANGTISE_PRIVATE, timeout=30)
    csv_dir = WORKSPACE.parent / "stockpool"
    if not csv_dir.exists():
        return []
    csv_files = sorted(csv_dir.glob("stockpool_stocks_*.csv"))
    if not csv_files:
        return []
    latest = csv_files[-1]
    stocks = []
    with open(latest, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            stocks.append({
                "code": row.get("security_code", ""),
                "name": row.get("security_abbr", ""),
            })
    return stocks


def _classify_stocks(stocks):
    """将自选股按市场分类：A股(SH/SZ/BJ)、港股(HK)、美股(O/N)、其他。"""
    a, hk, us, other = [], [], [], []
    for s in stocks:
        code = s.get("code", "").upper()
        # ADR（存托凭证）不支持行情查询
        if any(code.endswith(suf) for suf in (".O", ".N")):
            name = (s.get("name") or "").upper()
            # 有些 ADR 代码以 .O/.N 结尾但不是 ADR，保留
            us.append(s)
        elif code.endswith(".HK"):
            hk.append(s)
        elif any(code.endswith(suf) for suf in (".SH", ".SZ", ".BJ")):
            a.append(s)
        else:
            other.append(s)
    return a, hk, us, other


def get_quotes(stocks, trade_date):
    """拉取自选股行情 CSV，覆盖 A 股/港股/美股，合并为一张 QUOTES.csv。

    A股/H股：使用 trade_date（同一天）
    美股：使用前一日（BJT 17:00 跑复盘时，美盘当天尚未收盘）
    """
    if not stocks:
        return None
    from datetime import datetime, timedelta
    td = datetime.strptime(trade_date, "%Y-%m-%d")
    us_date = (td - timedelta(days=1)).strftime("%Y-%m-%d")

    a_stocks, hk_stocks, us_stocks, _ = _classify_stocks(stocks)
    all_csvs = []

    def _query(batch, date_label, market_tag):
        if not batch:
            return
        tmp_csv = WORKSPACE / trade_date / f"_tmp_quotes_{market_tag}.csv"
        write_securities_csv(batch, tmp_csv)
        script = GANGTISE_DATA / "quote.py"
        out = run([sys.executable, str(script),
            "--securities-file", str(tmp_csv),
            "-sd", date_label, "-ed", date_label,
            "--adjust", "forward",
        ], GANGTISE_DATA, timeout=120)
        # 从输出中找到所有 CSV 路径
        quote_dir = WORKSPACE.parent / "quote"
        for m in re.finditer(r'`([^`]+\.csv)`', out):
            p = Path(m.group(1))
            if p.exists():
                all_csvs.append(p)

    _query(a_stocks, trade_date, "a")
    _query(hk_stocks, trade_date, "hk")
    _query(us_stocks, us_date, "us")

    if not all_csvs:
        return None

    # 合并所有 CSV
    dest = WORKSPACE / trade_date / "QUOTES.csv"
    dest.parent.mkdir(parents=True, exist_ok=True)
    header_written = False
    with open(dest, "w", newline="", encoding="utf-8") as fout:
        for fpath in all_csvs:
            with open(fpath, newline="", encoding="utf-8") as fin:
                reader = csv.DictReader(fin)
                if not header_written:
                    fout.write(",".join(reader.fieldnames) + "\n")
                    header_written = True
                for row in reader:
                    fout.write(",".join(row.values()) + "\n")
    return str(dest)


def get_fund_flow(stocks, trade_date):
    """拉取自选股中 A 股的日资金流向。"""
    codes = [s for s in stocks if s["code"].upper().endswith((".SH", ".SZ", ".BJ"))]
    if not codes:
        return None
    tmp_csv = WORKSPACE / trade_date / "_tmp_ff_securities.csv"
    write_securities_csv(codes, tmp_csv)
    script = GANGTISE_DATA / "fund_flow.py"
    out = run([sys.executable, str(script),
        "--securities-file", str(tmp_csv),
        "-sd", trade_date, "-ed", trade_date,
    ], GANGTISE_DATA, timeout=120)
    ff_dir = WORKSPACE.parent / "fund_flow"
    path = extract_csv_path(out, known_dir=str(ff_dir) if ff_dir.exists() else None)
    if path and path.exists():
        dest = WORKSPACE / trade_date / "FUND_FLOW.csv"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
        return str(dest)
    return None


def get_announcements(stocks, trade_date):
    """获取公司公告，保存为 md。"""
    names = [s["name"] for s in stocks if s["name"]]
    if not names:
        return None
    results = []
    batch_size = 20
    for i in range(0, len(names), batch_size):
        batch = names[i:i+batch_size]
        script = GANGTISE_FILE / "announcement.py"
        out = run([sys.executable, str(script),
            "--securities", ",".join(batch),
            "-sd", trade_date, "-ed", trade_date,
            "-l", "30",
        ], GANGTISE_FILE, timeout=90)
        if out.strip():
            results.append(f"## 批次 {i//batch_size + 1}\n{out.strip()}")
    content = "\n\n".join(results) if results else "（无数据）"
    dest = WORKSPACE / trade_date / "ANNOUNCEMENTS.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        f.write(content)
    return str(dest)


def get_security_clues(stocks, trade_date):
    """获取投研线索（研究/观点）。"""
    names = [s["name"] for s in stocks if s["name"]]
    if not names:
        return None
    results = []
    batch_size = 10
    for i in range(0, len(names), batch_size):
        batch = names[i:i+batch_size]
        script = GANGTISE_AGENT / "security_clue.py"
        out = run([sys.executable, str(script),
            "--page-from", "0", "--page-size", "20",
            "-q", "bySecurity",
            "--securities", ",".join(batch),
            "-st", trade_date, "-et", trade_date,
        ], GANGTISE_AGENT, timeout=120)
        if out.strip():
            results.append(f"## 批次 {i//batch_size + 1}\n{out.strip()}")
    content = "\n\n".join(results) if results else "（无数据）"
    dest = WORKSPACE / trade_date / "CLUES.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        f.write(content)
    return str(dest)


def get_investment_calendar(trade_date):
    """获取未来一周投研日程。"""
    td = datetime.strptime(trade_date, "%Y-%m-%d")
    end_date = (td + timedelta(days=7)).strftime("%Y-%m-%d")
    results = {}
    for cal_type in ["roadshow", "site_visit", "strategy_meeting", "forum"]:
        script = GANGTISE_FILE / "investment_calendar.py"
        out = run([sys.executable, str(script),
            "-t", cal_type, "-sd", trade_date, "-ed", end_date, "-l", "20",
        ], GANGTISE_FILE, timeout=90)
        results[cal_type] = out.strip() or "（无数据）"
    content_parts = ["# 投研日程\n"]
    for t, c in results.items():
        content_parts.append(f"## {t}\n{c}\n")
    dest = WORKSPACE / trade_date / "CALENDAR.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        f.write("\n".join(content_parts))
    return str(dest)


def get_hk_indices_from_sina():
    """通过新浪实时行情 API 获取港股主要指数（恒生指数、恒生科技指数、国企指数）。
    
    API 返回格式（GBK 编码，逗号分隔的 JS 变量）：
        var hq_str_rt_hkHSI="HSI,恒生指数,今开,昨收,最高,最低,收盘,涨跌额,涨跌幅%,...";
    
    返回值示例：
        {
            "恒生指数": {"close": 24892.66, "change": -239.63, "change_pct": -0.95, ...},
            "恒生科技指数": {"close": 4668.23, "change": -146.60, "change_pct": -3.04, ...},
            "国企指数": {"close": 8251.07, ...}
        }
    失败时返回空 dict。
    """
    url = "https://hq.sinajs.cn/list=rt_hkHSI,rt_hkHSTECH,rt_hkHSCEI"
    req = urllib.request.Request(url, headers={
        "Referer": "https://finance.sina.com.cn",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    })
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        text = resp.read().decode("gbk")
    except Exception as e:
        print(f"[警告] 新浪港股指数 API 请求失败: {e}", file=sys.stderr)
        return {}

    result = {}
    for line in text.strip().splitlines():
        line = line.strip()
        if not line.startswith("var hq_str_rt_"):
            continue
        m = re.search(r'"(.+)"', line)
        if not m:
            continue
        fields = m.group(1).split(",")
        if len(fields) < 10:
            continue
        # 字段索引: 0=code, 1=name, 2=open, 3=prev_close, 4=high, 5=low, 6=close, 7=change, 8=change_pct
        code = fields[0]
        simp_name = {"HSI": "恒生指数", "HSTECH": "恒生科技指数", "HSCEI": "国企指数"}.get(code, fields[1])
        try:
            entry = {
                "open": float(fields[2]) if fields[2] else None,
                "prev_close": float(fields[3]) if fields[3] else None,
                "high": float(fields[4]) if fields[4] else None,
                "low": float(fields[5]) if fields[5] else None,
                "close": float(fields[6]) if fields[6] else None,
                "change": float(fields[7]) if fields[7] else None,
                "change_pct": float(fields[8]) if fields[8] else None,
            }
            result[simp_name] = entry
        except (ValueError, IndexError):
            continue
    return result


def get_index_data(trade_date):
    """获取大盘指数数据。
    
    A 股（上证指数/深证成指/创业板指/科创50）：使用 quote.py
    （industry_indicator 的 S25000024/S25000026 可能返回 nan，quote.py 更可靠）
    
    港股（恒生指数/恒生科技指数/国企指数）：使用新浪实时行情 API
    （industry_indicator 的 M00015437 取值时点可能非收盘竞价后收盘价，
     且行业主题指数搜索恒生科技相关指标持续 HTTP 500）
    """
    result = {}

    # ── A 股指数：quote.py ──
    # 注意：quote.py 的 CSV 列名为中文（收盘价、涨跌幅等）
    COL_MAP = {"收盘价": "close", "涨跌幅": "change_pct", "开盘价": "open",
               "最高价": "high", "最低价": "low", "成交额": "volume"}
    quote_scripts_dir = GANGTISE_DATA
    index_codes = "000001.SH,399001.SZ,399006.SZ,000688.SH"
    out = run([sys.executable, str(quote_scripts_dir / "quote.py"),
        "--securities", index_codes,
        "-sd", trade_date, "-ed", trade_date,
    ], quote_scripts_dir, timeout=60)
    csv_path = extract_csv_path(out, known_dir=str(WORKSPACE.parent / "quote") if (WORKSPACE.parent / "quote").exists() else None)
    if csv_path and csv_path.exists():
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = row.get("security_code", "")
                name_map = {
                    "000001.SH": "上证指数",
                    "399001.SZ": "深证成指",
                    "399006.SZ": "创业板指",
                    "000688.SH": "科创50",
                }
                display_name = name_map.get(code, code)
                entry = {}
                for cn_key, en_key in COL_MAP.items():
                    val = row.get(cn_key, "nan")
                    if val and val != "nan":
                        try:
                            entry[en_key] = float(val)
                        except ValueError:
                            pass
                if "close" in entry:
                    result[display_name] = entry

    # ── 港股指数：新浪实时行情 API ──
    hk_data = get_hk_indices_from_sina()
    if hk_data:
        for name, data in hk_data.items():
            result[name] = {
                "close": data.get("close"),
                "change": data.get("change"),
                "change_pct": data.get("change_pct"),
                "open": data.get("open"),
                "high": data.get("high"),
                "low": data.get("low"),
                "prev_close": data.get("prev_close"),
            }

    return result


def get_market_turnover(trade_date):
    """获取两市成交额。
    
    优先使用 Gangtise industry_indicator：
    - 沪市成交额: M00015740（成交额:股票:沪市:当日值，单位：亿元）
    - 深市成交额: M00005612（成交额:深市:A股:当日值，单位：百万元）
    
    回退方案：当 industry_indicator 返回为空时，用 quote.py 指数行情中的成交额字段
    （上证指数成交额=沪市，深证成指成交额=深市，单位：元→亿元÷1e8）
    """
    indicators = "M00015740,M00005612"
    script = GANGTISE_DATA / "industry_indicator.py"
    out = run([sys.executable, str(script),
        "-m", "get",
        "--indicators", indicators,
        "-sd", trade_date, "-ed", trade_date,
    ], GANGTISE_DATA, timeout=60)
    
    csv_path = extract_csv_path(out, known_dir=str(WORKSPACE.parent / "industry_indicator") if (WORKSPACE.parent / "industry_indicator").exists() else None)
    result = {}
    if csv_path and csv_path.exists():
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                sh = row.get("M00015740", "nan")
                sz = row.get("M00005612", "nan")
                if sh and sh != "nan":
                    result["沪市"] = float(sh)
                if sz and sz != "nan":
                    result["深市"] = float(sz) / 100  # 百万元→亿元
                if "沪市" in result and "深市" in result:
                    result["两市合计"] = round(result["沪市"] + result["深市"], 2)

    # 回退：若 industry_indicator 数据不全，用 quote.py 的成交额补缺
    if not result.get("沪市") or not result.get("深市"):
        idx_from_quote = _get_turnover_from_quote(trade_date)
        if idx_from_quote:
            if not result.get("沪市") and idx_from_quote.get("沪市"):
                result["沪市"] = idx_from_quote["沪市"]
            if not result.get("深市") and idx_from_quote.get("深市"):
                result["深市"] = idx_from_quote["深市"]
            if "沪市" in result and "深市" in result:
                result["两市合计"] = round(result["沪市"] + result["深市"], 2)

    return result


def _get_turnover_from_quote(trade_date):
    """从 quote.py 指数行情获取两市成交额（回退方案）。"""
    quote_scripts_dir = GANGTISE_DATA
    out = run([sys.executable, str(quote_scripts_dir / "quote.py"),
        "--securities", "000001.SH,399001.SZ",
        "-sd", trade_date, "-ed", trade_date,
    ], quote_scripts_dir, timeout=60)
    csv_path = extract_csv_path(out, known_dir=str(WORKSPACE.parent / "quote") if (WORKSPACE.parent / "quote").exists() else None)
    result = {}
    if csv_path and csv_path.exists():
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = row.get("security_code", "")
                vol_str = row.get("成交额", "nan")
                try:
                    vol = float(vol_str) if vol_str and vol_str != "nan" else 0
                except ValueError:
                    vol = 0
                if code == "000001.SH":
                    result["沪市"] = round(vol / 1e8, 2)  # 元→亿元
                elif code == "399001.SZ":
                    result["深市"] = round(vol / 1e8, 2)
    return result


def get_one_line_summaries(stocks, trade_date):
    """获取个股一句话总结。"""
    codes = [s["code"] for s in stocks]
    if not codes:
        return None
    results = []
    batch_size = 30
    for i in range(0, len(codes), batch_size):
        batch = codes[i:i+batch_size]
        script = GANGTISE_AGENT / "agents.py"
        out = run([sys.executable, str(script),
            "-a", "stock-one-line-summary",
            "--securities", ",".join(batch),
        ], GANGTISE_AGENT, timeout=180)
        if out.strip():
            results.append(out.strip())
    content = "\n\n---\n\n".join(results) if results else "（无数据）"
    dest = WORKSPACE / trade_date / "ONE_LINE_SUMMARIES.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        f.write(content)
    return str(dest)


def main():
    parser = argparse.ArgumentParser(description="自选股复盘数据采集")
    parser.add_argument("--date", default=date.today().strftime("%Y-%m-%d"), help="交易日")
    parser.add_argument("--skip-stockpool", action="store_true")
    parser.add_argument("--skip-quotes", action="store_true")
    parser.add_argument("--skip-fundflow", action="store_true")
    parser.add_argument("--skip-announcements", action="store_true")
    parser.add_argument("--skip-clues", action="store_true")
    parser.add_argument("--skip-calendar", action="store_true")
    parser.add_argument("--skip-summaries", action="store_true")
    parser.add_argument("--skip-index", action="store_true")
    parser.add_argument("--skip-turnover", action="store_true")
    args = parser.parse_args()
    td = args.date

    # 1. 自选股
    stocks = get_stockpool() if not args.skip_stockpool else []
    if not stocks:
        print("[错误] 未获取到自选股，请检查 Gangtise 凭证及 stockpool.py 运行情况。", file=sys.stderr)
        sys.exit(1)
    print(f"[OK] 自选股: {len(stocks)} 只")

    # 2. 行情
    qp = get_quotes(stocks, td) if not args.skip_quotes else None
    print(f"[OK] 行情: {qp or '无数据'}")

    # 3. 资金流向
    fp = get_fund_flow(stocks, td) if not args.skip_fundflow else None
    print(f"[OK] 资金流向: {fp or '无数据'}")

    # 4. 公告
    ap = get_announcements(stocks, td) if not args.skip_announcements else None
    print(f"[OK] 公告: {ap or '无数据'}")

    # 5. 投研线索
    cp = get_security_clues(stocks, td) if not args.skip_clues else None
    print(f"[OK] 投研线索: {cp or '无数据'}")

    # 6. 投研日程
    calp = get_investment_calendar(td) if not args.skip_calendar else None
    print(f"[OK] 投研日程: {calp or '无数据'}")

    # 7. 一句话总结
    sp = get_one_line_summaries(stocks, td) if not args.skip_summaries else None
    print(f"[OK] 一句话总结: {sp or '无数据'}")

    # 8. 大盘指数数据
    idx = get_index_data(td) if not args.skip_index else None
    print(f"[OK] 大盘指数: {idx or '无数据'}")

    # 9. 两市成交额
    tover = get_market_turnover(td) if not args.skip_turnover else None
    print(f"[OK] 两市成交额: {tover or '无数据'}")

    # 汇总 JSON
    out_dir = WORKSPACE / td
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "date": td,
        "stock_count": len(stocks),
        "stocks": stocks,
        "index_data": idx,
        "market_turnover": tover,
        "files": {
            "quotes": qp,
            "fund_flow": fp,
            "announcements": ap,
            "clues": cp,
            "calendar": calp,
            "summaries": sp,
        },
    }
    jpath = out_dir / "data.json"
    with open(jpath, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] 数据汇总: {jpath}")


if __name__ == "__main__":
    main()
