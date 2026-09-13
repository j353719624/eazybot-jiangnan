# EazyBot-jiangnan（Apple Silicon arm64 专仓）

> 本仓库只发布 **Apple Silicon (arm64)** 版本的源码与 Release；Intel 版在 [eazybot-claw](https://github.com/j353719624/eazybot-claw)。

基于官方 EazyBot 1.0.7 桌面包的 fork。本仓库保存**全部定制源码与构建脚本**，
不包含第三方运行时（env/）与官方 console 全量产物。

## 定制内容

| 模块 | 说明 |
|---|---|
| `launcher/launcher.c` | 单进程启动器：exec 到 `Contents/MacOS/EazyBot-jiangnan`（venv python 真身副本），显式 envp 设置 `__PYVENV_LAUNCHER__` 等变量。解决 LaunchServices 归属导致的 **Dock 双图标** 问题 |
| `overlay/.../release_bootstrap.py` | 启动引导：加载 release.env、首次播种种子数据、darwin 分支最终 exec 回 `EAZYBOT_MACOS_PYTHON`（并补回被 CPython 弹掉的 `__PYVENV_LAUNCHER__`） |
| `overlay/.../workflow_plus/` | 工作流模块：DAG 调度 + 子代理并行 + 条件路由（success/failure/always），含画布页面 `/workflow-plus/page` |
| `overlay/.../desktop_static_server.py` | Console 静态服务：catch-all 内显式分支服务工作流页面（no-store） |
| `overlay/.../app/_app.py` | 挂载 workflow_plus 路由（`/api` 前缀 + 根路径页面） |
| `overlay/.../console/assets/index-BiWh193y.js` | 三按钮补丁：欢迎页/聊天页顶栏恒用 `variant:"full"`（申请续费/升级套餐、配置岗底斯密钥、下载终端申请openAPI） |
| `seed/eazybot-data/` | 首启播种数据：30 技能 + 6 智能体工作区 + gangtise-mcp（金融分析助手，`$GTS_*` 引用写法，配齐密钥后自动启用）。**不含任何凭据**（.secret/会话/日志均排除） |

## 从基础包构建 DMG（双架构）

```bash
chmod +x scripts/build-dmg.sh

# Intel（基础包：官方 1.0.7 mac x64，env 已组装、venv python 已改名 EazyBot-jiangnan）
./scripts/build-dmg.sh x64   /path/to/官方x64基础包/EazyBot-jiangnan.app ./dist

# Apple Silicon（基础包：官方 1.0.7 mac arm64；脚本自动换牌 + 换算 python 副本 +
# 交叉编译 arm64 启动器并 adhoc 签名；icns 取自本机已装的 x64 定制版，可用
# EAZYBOT_X64_APP 环境变量指向其它来源）
./scripts/build-dmg.sh arm64 /path/to/官方arm64基础包/EazyBot.app ./dist
```

脚本流程：复制基础包 → 应用 overlay → 架构相关处理（启动器编译/换牌/python 副本）
→ 清 console 预压缩缓存 → 放入种子 → 打 DMG。

> 运行时（python 解释器与 C 扩展 .so）是机器码，无法在本机跨架构编译；
> arm64 版取官方 arm64 基础包的运行时（版本与 x64 完全一致：后端 2.2.18、
> agentscope 1.0.19.post1、reme_ai 0.3.1.8、agentscope_runtime 1.1.4），
> 其余内容（后端补丁/console/种子/品牌/配置）全部来自本仓库 overlay 与 seed。

## 关键机制备忘

- **单 Dock 图标**：LS 只归属 `Contents/MacOS/` 下的可执行文件；python 必须从
  MacOS 副本启动，且最终 exec（bootstrap 二次 execve）不能回落到 env/bin。
- **CPython 坑**：解释器读取 `__PYVENV_LAUNCHER__` 后会把它从 `os.environ` 弹掉，
  二次 exec 时必须重新补上，否则 MacOS 副本解析不到 pyvenv.cfg。
- **密钥安全**：种子里 MCP headers 用 `$VAR` 引用（`/envs` 接口下发真实值）；
  严禁把 API 返回的掩码值（`$G*********_KEY`）写回配置——后端按 `$VAR` 扫描
  缺失变量，`*` 会截断变量名导致配置密钥弹窗异常。

## Releases

`EazyBot-jiangnan-1.0.7-mac-x64.dmg`：拖入 Applications 安装。首启自动播种
智能体/技能/MCP；登录后按账号同步企业数据。
