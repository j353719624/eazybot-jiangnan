#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SAP GUI 命令行工具（Skill 用）— 直接调用 SAPGuiController，无需 MCP 服务器。

用法示例：
  python sap_cli.py status                       # 查看当前 SAP GUI 连接/会话
  python sap_cli.py connect-existing             # 接管已打开的 SAP 窗口（默认第 1 个连接第 1 个会话）
  python sap_cli.py connect-existing --conn 1 --sess 0
  python sap_cli.py tcode VA03                   # 执行事务码
  python sap_cli.py screen                       # 读取当前屏幕元素清单
  python sap_cli.py read wnd[0]/usr/txtMATNR     # 读字段
  python sap_cli.py set wnd[0]/usr/txtMATNR 123  # 写字段
  python sap_cli.py button wnd[0]/usr/btnOK      # 点按钮
  python sap_cli.py enter                        # 回车（F8=执行 b=返回 F3 F12=取消 save=保存）
  python sap_cli.py vkey 0                       # 自定义 vkey
  python sap_cli.py table wnd[0]/usr/tblXXX --max-rows 50
  python sap_cli.py cell wnd[0]/usr/tblXXX 0 MATNR          # 读单元格
  python sap_cli.py setcell wnd[0]/usr/tblXXX 0 MATNR 1000  # 改单元格
  python sap_cli.py selrow wnd[0]/usr/tblXXX 2              # 选中表格行
  python sap_cli.py dblcell wnd[0]/usr/tblXXX 0 MATNR       # 双击单元格
  python sap_cli.py popup                        # 读取当前弹窗
  python sap_cli.py statusbar                    # 读状态栏消息
  python sap_cli.py combo wnd[0]/usr/cmbXXX      # 列出下拉框选项
  python sap_cli.py tree wnd[0]/usr/tctXXX       # 读树控件
  python sap_cli.py screenshot out.png           # 截图

所有输出均为 UTF-8 JSON（stdout）。
"""

import argparse
import json
import sys

# 保证脚本可独立运行（不要求 pip 安装本包）
if __package__ in (None, ""):
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_sap_gui import SAPGUIController, SAPGUIError

CTRL = SAPGUIController()


def out(data):
    """输出 UTF-8 JSON（Windows 控制台默认 GBK，强制 UTF-8 防止中文乱码）。"""
    text = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    sys.stdout.buffer.write(text.encode("utf-8"))
    sys.stdout.buffer.write(b"\n")


def die(msg):
    out({"error": msg})
    sys.exit(1)


def _connect_existing(conn, sess):
    info = CTRL.connect_to_existing_session(connection_index=conn, session_index=sess)
    return info.__dict__ if hasattr(info, "__dict__") else str(info)


def main():
    p = argparse.ArgumentParser(description="SAP GUI automation CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status")
    sp = sub.add_parser("connect-existing")
    sp.add_argument("--conn", type=int, default=0)
    sp.add_argument("--sess", type=int, default=0)

    sp = sub.add_parser("tcode"); sp.add_argument("code")
    sub.add_parser("screen")

    sp = sub.add_parser("read"); sp.add_argument("field_id")
    sp = sub.add_parser("set"); sp.add_argument("field_id"); sp.add_argument("value")
    sp = sub.add_parser("button"); sp.add_argument("element_id")
    sp = sub.add_parser("menu"); sp.add_argument("menu_id")
    sp = sub.add_parser("check"); sp.add_argument("checkbox_id"); sp.add_argument("state", nargs="?", default="1")
    sp = sub.add_parser("radio"); sp.add_argument("radio_id")
    sp = sub.add_parser("combo"); sp.add_argument("combobox_id"); sp.add_argument("key", nargs="?")
    sp = sub.add_parser("tab"); sp.add_argument("tab_id")
    sp = sub.add_parser("focus"); sp.add_argument("element_id")

    sub.add_parser("enter"); sub.add_parser("back"); sub.add_parser("save"); sub.add_parser("cancel"); sub.add_parser("execute")
    sp = sub.add_parser("vkey"); sp.add_argument("key", type=int)

    sp = sub.add_parser("table"); sp.add_argument("table_id")
    sp.add_argument("--max-rows", type=int, default=100)
    sp = sub.add_parser("cell"); sp.add_argument("grid_id"); sp.add_argument("row", type=int); sp.add_argument("column")
    sp = sub.add_parser("setcell"); sp.add_argument("grid_id"); sp.add_argument("row", type=int); sp.add_argument("column"); sp.add_argument("value")
    sp = sub.add_parser("selrow"); sp.add_argument("table_id"); sp.add_argument("row", type=int)
    sp = sub.add_parser("dblcell"); sp.add_argument("grid_id"); sp.add_argument("row", type=int); sp.add_argument("column")

    sub.add_parser("popup"); sub.add_parser("statusbar")
    sp = sub.add_parser("tree"); sp.add_argument("tree_id")
    sp = sub.add_parser("treenode"); sp.add_argument("tree_id"); sp.add_argument("node_key")
    sp = sub.add_parser("screenshot"); sp.add_argument("filepath", nargs="?", default="")

    args = p.parse_args()
    try:
        # 自动接管：除 status/connect-existing 外，若当前进程未连接，
        # 则自动接管第一个已打开的 SAP 会话（每次 CLI 运行都是新进程，
        # 连接状态不持久化，必须自动重连）
        if args.cmd not in ("status", "connect-existing"):
            _connected = CTRL.is_connected
            _ok = _connected() if callable(_connected) else _connected
            if not _ok:
                CTRL.connect_to_existing_session(0, 0)

        if args.cmd == "status":
            connected = CTRL.is_connected
            result = {"connected": connected() if callable(connected) else connected,
                      "connections": CTRL.list_connections()}
        elif args.cmd == "connect-existing":
            result = {"connected": _connect_existing(args.conn, args.sess)}
        elif args.cmd == "tcode":
            result = CTRL.execute_transaction(args.tcode if hasattr(args, "tcode") else args.code)
        elif args.cmd == "screen":
            result = CTRL.get_screen_info()
        elif args.cmd == "read":
            result = CTRL.read_field(args.field_id)
        elif args.cmd == "set":
            result = CTRL.set_field(args.field_id, args.value)
        elif args.cmd == "button":
            result = CTRL.press_button(args.element_id)
        elif args.cmd == "menu":
            result = CTRL.select_menu(args.menu_id)
        elif args.cmd == "check":
            result = CTRL.select_checkbox(args.checkbox_id, args.state not in ("0", "false", "off"))
        elif args.cmd == "radio":
            result = CTRL.select_radio_button(args.radio_id)
        elif args.cmd == "combo":
            result = (CTRL.select_combobox_entry(args.combobox_id, args.key)
                      if args.key else CTRL.get_combobox_entries(args.combobox_id))
        elif args.cmd == "tab":
            result = CTRL.select_tab(args.tab_id)
        elif args.cmd == "focus":
            result = CTRL.set_focus(args.element_id)
        elif args.cmd == "enter":
            result = CTRL.press_enter()
        elif args.cmd == "back":
            result = CTRL.press_back()
        elif args.cmd == "save":
            result = CTRL.press_save()
        elif args.cmd == "cancel":
            result = CTRL.press_cancel()
        elif args.cmd == "execute":
            result = CTRL.press_execute()
        elif args.cmd == "vkey":
            result = CTRL.send_vkey(args.key)
        elif args.cmd == "table":
            result = CTRL.read_table(args.table_id, max_rows=args.max_rows)
        elif args.cmd == "cell":
            result = CTRL.get_cell(args.grid_id, args.row, args.column) \
                if hasattr(CTRL, "get_cell") else \
                CTRL.modify_cell(args.grid_id, args.row, args.column, None)
        elif args.cmd == "setcell":
            result = CTRL.modify_cell(args.grid_id, args.row, args.column, args.value)
        elif args.cmd == "selrow":
            result = CTRL.select_table_row(args.table_id, args.row)
        elif args.cmd == "dblcell":
            result = CTRL.double_click_table_cell(args.grid_id, args.row, args.column)
        elif args.cmd == "popup":
            result = CTRL.get_popup_window()
        elif args.cmd == "statusbar":
            result = CTRL.get_status_bar() if hasattr(CTRL, "get_status_bar") \
                else {"hint": "use 'screen' or read wnd[0]/sbar"}
        elif args.cmd == "tree":
            result = CTRL.get_tree_info(args.tree_id) if hasattr(CTRL, "get_tree_info") \
                else CTRL.read_tree(args.tree_id)
        elif args.cmd == "treenode":
            result = CTRL.select_tree_node(args.tree_id, args.node_key)
        elif args.cmd == "screenshot":
            result = CTRL.take_screenshot(args.filepath or None)
        else:
            die(f"未知命令: {args.cmd}")
        out(result)
    except SAPGUIError as e:
        die(str(e))
    except Exception as e:
        die(f"{type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
