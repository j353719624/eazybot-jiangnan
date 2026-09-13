---
description: 将当前智能体拥有的技能（skills 目录下的技能文件夹）或智能体配置（AGENTS.md/SOUL.md/PROFILE.md/MEMORY.md
  等）选择性地上传到自建 Gitea 仓库。触发场景：用户提到"上传技能"、"上传到 gitea"、"同步技能到代码仓库"、"把智能体配置上传到 gitea"等。
metadata:
  eazybot:
    emoji: "\U0001F680"
    requires:
    - git
name: gitea_upload
---

# 技能上传到 Gitea

把本智能体的技能/配置上传到 Gitea 仓库：`http://192.168.9.192:88/luyongchao/easybot-skills`

## 使用流程（Agent 按此执行）

1. **列出可选技能**（供用户选择）：

```powershell
powershell -ExecutionPolicy Bypass -File "<本技能目录>\scripts\upload_skills.ps1" -ListOnly
```

2. **让用户选择**：把编号清单展示给用户，问要上传哪几个（支持 `1,3-5`、`all`）。若用户在消息里已经指明了技能名，可跳过询问。

3. **执行上传**（命令行模式，推荐）：

```powershell
powershell -ExecutionPolicy Bypass -File "<本技能目录>\scripts\upload_skills.ps1" -Names "docx,pdf" -Message "上传说明"
```

参数：
- `-Names "a,b,c"`：按技能目录名上传（支持逗号分隔多个）
- `-All`：上传全部技能
参数：
- `-Names "a,b,c"`：按技能目录名上传（支持逗号分隔多个）
- `-All`：上传全部技能
- `-Bundle`：**上传整个智能体**（全部技能 + 配置文件 4 件套），一条命令完成；常与 `-Agent` 组合，如 `-Agent "bf99cb" -Bundle`
- `-Profile`：同时上传智能体配置（AGENTS.md、SOUL.md、PROFILE.md、MEMORY.md）到仓库 `agents/<智能体名>/` 目录
- `-Message "xxx"`：自定义 commit message（默认自动生成，含技能名和日期）
- `-ListOnly`：仅列出技能清单，不执行上传
- `-Agent "<id或id片段>"`：指定其他智能体（如 `-Agent "2eab2f"` 指江南数字管家），上传它的技能/配置；不带则为当前智能体
- `-ListAgents`：列出所有智能体工作空间及各自技能数
- `-Diff`：与 Gitea 远端对比，报告「新增（远端没有）/更新（将覆盖）/远端独有」；单独使用只报告不上传

4. **上传前差异报告**：建议上传时带 `-Diff`，会先打印该智能体相对远端的新增/覆盖清单，方便确认。

## 上传整个智能体（推荐用法）

用户说「把 xx 智能体上传到 gitea」时，用 `-Bundle`：

```powershell
powershell -ExecutionPolicy Bypass -File "<本技能目录>\scripts\upload_skills.ps1" -Agent "<id或片段>" -Bundle
```

等价于 `-All -Profile`：把该智能体的全部技能和 4 个配置文件（AGENTS/SOUL/PROFILE/MEMORY.md）写入仓库 `agents/<智能体名>/` 并推送。

## 技能审计报告（谁缺哪些技能、哪些没上传）

```powershell
powershell -ExecutionPolicy Bypass -File "<本技能目录>\scripts\agent_skill_report.ps1"
```

输出：所有智能体的技能清单、每个智能体相对技能全池缺少哪些技能、技能分布矩阵、哪些技能尚未上传到 Gitea。

4. **验证**：push 成功后提示用户在 Gitea Web 界面确认。

## 交互模式

不带 `-Names` 且不带 `-All` 运行时，脚本进入交互模式：编号列出技能，用户输入序号（支持 `1,3-5` 或 `all`）。

## 首次使用（凭据配置）

首次 push 时 Windows 凭据管理器（GCM）会弹出窗口，需要用户输入 Gitea 用户名和 Access Token（Gitea 网页 → 设置 → 应用 → 生成令牌，勾选 repo 权限）。凭据只存 Windows 凭据管理器，**绝不写入任何文件**。

⚠️ 本仓库走 HTTP（非 HTTPS），若 GCM 拒绝不安全远程，先执行一次：

```powershell
git config --global credential.http://192.168.9.192:88.provider generic
git config --global credential.allowUnsafeRemotes true
```

## 常见错误处理

- **push 被拒绝（non-fast-forward）**：脚本已自动 `git pull --rebase` 再 push；若仍冲突，提示用户远端有他人提交，需人工处理。
- **认证失败**：在凭据管理器中删除 `git:http://192.168.9.192:88` 条目后重新推送，或让用户重新生成 token。
- **网络不通**：确认在内网环境，可用 `git ls-remote http://192.168.9.192:88/luyongchao/easybot-skills` 探测。
- **技能名含中文/空格**：脚本内部已对路径加引号处理，直接传目录名即可。

## 本地仓库副本

首次运行会自动 clone 到智能体工作空间下的 `gitea-skills-repo\`，之后增量 pull + 复制 + commit + push。同步策略为**只增不删**（本地删除技能不会从远端删除）。