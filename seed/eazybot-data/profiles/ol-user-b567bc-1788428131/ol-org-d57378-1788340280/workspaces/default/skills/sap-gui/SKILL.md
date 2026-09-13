---
description: 通过 SAP GUI Scripting COM 接口直接操作 SAP GUI——读写字段、表格、树、弹窗，执行事务码，截图。当用户提到
  SAP、SAP GUI、事务码（如 VA03、MM03、FBL5N）、SAP 表格/ALV 操作、SAP 自动化时使用。仅限 Windows + 已安装 SAP
  GUI。
name: sap-gui
---

# SAP GUI 操作 Skill

本 skill 让 agent 通过命令行直接控制 SAP GUI for Windows（无需 MCP 服务器）。
核心是 `mcp_sap_gui` Python 包（源自 mcp-sap-gui 项目，已去除 fastmcp 依赖），
封装在 `sap_cli.py` 中，所有输出为 UTF-8 JSON。

## 前提条件

1. Windows + 已安装 SAP GUI for Windows
2. SAP GUI 脚本功能已启用（RZ11 中 `sapgui/user_scripting` = TRUE，默认开启；
   用户端：选项 → 辅助功能与脚本 → 启用脚本）
3. Python 3.10+ 且已安装 `pywin32`（`pip install pywin32`）

## 工作流

1. **先看连接**：`python skills/sap-gui/sap_cli.py status` — 列出已打开的 SAP 连接。
2. **接管会话**：`python skills/sap-gui/sap_cli.py connect-existing`（`--conn N --sess M` 选定）。
3. **然后正常操作**。

## 常用命令

```bash
S="skills/sap-gui/sap_cli.py"

# 连接与导航
python $S status              # 列出连接/会话
python $S connect-existing    # 接管已打开窗口
python $S tcode VA03          # 进入事务码（也可直接 /nVA03）
python $S screen              # 读当前屏幕全部元素（找到字段 ID）
python $S popup               # 读弹窗（标题/正文/按钮/分类）
python $S statusbar           # 操作结果看状态栏消息

# 字段
python $S read   wnd[0]/usr/txtMATNR
python $S set    wnd[0]/usr/txtMATNR 100-100
python $S check  wnd[0]/usr/chkXXX 1      # 勾选/取消(0)
python $S radio  wnd[0]/usr/radXXX
python $S combo  wnd[0]/usr/cmbXXX        # 不带值=列出选项
python $S combo  wnd[0]/usr/cmbXXX KEY    # 选择选项
python $S tab    wnd[0]/usr/tabsXXX_TAB/tabpXXX   # 切换标签页
python $S button wnd[0]/usr/btnXXX
python $S menu   wnd[0]/mbar/menu[0]/menu[2]      # 菜单项

# 回车/导航（等价按键）
python $S enter     # 回车 = vkey 0
python $S save      # Ctrl+S
python $S back      # F3 返回
python $S cancel    # F12 取消
python $S execute   # F8 执行
python $S vkey 4    # 任意 vkey（0=回车 3=F3 8=F8 11=Ctrl+S 12=F12）

# 表格 / ALV
python $S table   wnd[0]/usr/tblSAPMV45A_POS --max-rows 50
python $S cell    wnd[0]/usr/tblXXX 0 MATNR          # 读单元格
python $S setcell wnd[0]/usr/tblXXX 0 MATNR 1000     # 改单元格
python $S selrow  wnd[0]/usr/tblXXX 2                # 选中行
python $S dblcell wnd[0]/usr/tblXXX 0 MATNR          # 双击单元格

# 树
python $S tree wnd[0]/usr/tctXXX          # 读树结构
python $S treenode wnd[0]/usr/tctXXX NODEKEY      # 展开选中节点

# 截图（需 pillow）
python $S screenshot sap.png
```

## 关键经验

- **元素 ID 从 `screen` 命令获取**，不要猜。格式如 `wnd[0]/usr/txtXXX`、`wnd[1]` 是弹窗。
- **写操作前先 `screen` 确认字段存在且可改**；写入后用 `read` 验证。
- **每步操作后看状态栏/弹窗**：`statusbar` 和 `popup` 能及时发现错误消息。
- **弹窗分类关键词是英文**（"error"/"save changes" 等）。中文 SAP 环境下分类可能失效，
  但弹窗文本仍会原样返回，agent 应自己根据中文内容判断下一步。
- **保存类操作先跟用户确认**（改主数据、过账、删除等），确认后再 `save`。
- **`set_field` 不触发校验**，需要按回车（`enter`）才会触发 SAP 校验。
- 中文值直接传即可，COM 层是 Unicode（UTF-16 BSTR），读写的中文都能正常往返。
- 若 COM 连接偶发失败（GUI 重启后），重新 `connect-existing` 即可。

## 错误处理

所有错误输出为 `{"error": "..."}`，常见：
- `Not connected to SAP` → 先 connect-existing
- `pywin32 is required` → pip install pywin32
- 元素找不到 → ID 错了或屏幕变了，重新跑 `screen`