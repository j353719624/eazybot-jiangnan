# upload_skills.ps1 - 将 EazyBot 技能/配置上传到自建 Gitea
# 用法示例：
#   仅列出技能:      powershell -File upload_skills.ps1 -ListOnly
#   上传指定技能:    powershell -File upload_skills.ps1 -Names "docx,pdf"
#   上传全部技能:    powershell -File upload_skills.ps1 -All
#   上传+智能体配置: powershell -File upload_skills.ps1 -Names "docx" -Profile
#   指定其他智能体:  powershell -File upload_skills.ps1 -Agent "2eab2f" -All
#   列出所有智能体:  powershell -File upload_skills.ps1 -ListAgents
#   对比远端差异:    powershell -File upload_skills.ps1 -Diff
param(
    [string]$Names = "",
    [switch]$All,
    [switch]$Profile,
    [switch]$ListOnly,
    [string]$Message = "",
    [string]$Agent = "",
    [switch]$ListAgents,
    [switch]$Diff,
    [switch]$Bundle
)

$ErrorActionPreference = "Stop"

# -Bundle = 上传目标智能体的全部技能 + 配置文件（完整智能体快照）
if ($Bundle) { $All = $true; $Profile = $true }

# ---- 路径定义 ----
$SkillRoot0 = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSCommandPath))   # 本技能的 ...\workspaces\<id>\skills
$DefaultWs  = Split-Path -Parent $SkillRoot0                                                # 脚本所在智能体的 ...\workspaces\<id>
$WsRoot     = Split-Path -Parent $DefaultWs                                                 # ...\workspaces
$Workspace  = $DefaultWs                                                                    # 目标智能体工作空间（可被 -Agent 改变）
$RepoDir    = Join-Path $DefaultWs "gitea-skills-repo"
$RepoUrl    = "http://192.168.9.192:88/luyongchao/easybot-skills"
$ProfileFiles = @("AGENTS.md", "SOUL.md", "PROFILE.md", "MEMORY.md")

# ---- 解析 -Agent：定位目标智能体工作空间 ----
if ($Agent -ne "") {
    $cands = Get-ChildItem -LiteralPath $WsRoot -Directory | Where-Object { $_.Name -like "*$Agent*" }
    if (-not $cands) { throw "未找到工作空间匹配 '$Agent'（用 -ListAgents 查看所有智能体）" }
    if ($cands.Count -gt 1) { throw "匹配到多个工作空间: $(($cands | ForEach-Object Name) -join ', ')，请用更完整的 ID" }
    $Workspace = $cands[0].FullName
    Write-Host "目标智能体工作空间: $Workspace"
}
$SkillsDir = Join-Path $Workspace "skills"

# ---- 工作空间 ID -> 仓库目录名 映射（须与仓库 README.md 保持一致）----
$AgentMap = @{
    "default"                     = "办公助手"
    "ent_ol-aa-2eab2f-1788952009" = "江南数字管家"
    "ent_ol-aa-8e1c25-1789006552" = "TMS物流助手"
    "ent_ol-aa-bf99cb-1789004354" = "电缆合同识别助手"
    "ent_ol-aa-dbe74e-1789017120" = "SAP_GUI自动化助手"
}
function Get-AgentDirName([string]$WsId) {
    if ($AgentMap.ContainsKey($WsId)) { return $AgentMap[$WsId] }
    return $WsId   # 未知智能体直接用工作空间 ID 作目录名
}
$AgentDirName = Get-AgentDirName (Split-Path -Leaf $Workspace)
Write-Host "仓库目标目录: agents/$AgentDirName"

# ---- 工具函数 ----
function Get-SkillDirs {
    Get-ChildItem -LiteralPath $SkillsDir -Directory | Where-Object {
        Test-Path -LiteralPath (Join-Path $_.FullName "SKILL.md")
    } | Sort-Object Name
}

function Show-AgentList {
    Write-Host "所有智能体工作空间："
    Get-ChildItem -LiteralPath $WsRoot -Directory | ForEach-Object {
        $sk = Join-Path $_.FullName "skills"
        $n = 0
        if (Test-Path -LiteralPath $sk) {
            $n = @(Get-ChildItem -LiteralPath $sk -Directory | Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName "SKILL.md") }).Count
        }
        $cur = if ($_.FullName -ieq $DefaultWs) { "   <- 当前" } elseif ($Diff) {
    # 仅 -Diff（无 -Names/-All）：对比全部技能与远端，只报告不上传
    $selected = $dirs
} else { "" }
        Write-Host ("  {0}  ({1} 个技能){2}" -f $_.Name, $n, $cur)
    }
}

function Resolve-Selection([string]$Input_) {
    # 解析 "1,3-5" / "all" 形式的选择，返回技能目录对象数组
    $dirs = Get-SkillDirs
    if (-not $dirs) { throw "未在 $SkillsDir 找到任何包含 SKILL.md 的技能目录" }
    $idx = @()
    foreach ($part in ($Input_ -split ',')) {
        $part = $part.Trim()
        if ($part -match '^(\d+)\s*-\s*(\d+)$') {
            $idx += [int]$Matches[1]..[int]$Matches[2]
        } elseif ($part -match '^\d+$') {
            $idx += [int]$part
        } elseif ($part -ne "") {
            throw "无法解析的选择项: '$part'（请用序号，如 1,3-5 或 all）"
        }
    }
    $idx = $idx | Where-Object { $_ -ge 1 -and $_ -le $dirs.Count } | Select-Object -Unique
    if (-not $idx) { throw "没有有效的选择项" }
    $idx | ForEach-Object { $dirs[$_-1] }
}

function Copy-SkillToRepo($Dir) {
    $dest = Join-Path $RepoDir ("agents\" + $AgentDirName + "\skills\" + $Dir.Name)
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    Copy-Item -Path (Join-Path $Dir.FullName "*") -Destination $dest -Recurse -Force
    Write-Host "  已复制: $($Dir.Name) -> agents/$AgentDirName/skills/$($Dir.Name)"
}

function Copy-ProfileToRepo {
    $dest = Join-Path $RepoDir ("agents\" + $AgentDirName)
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    foreach ($f in $ProfileFiles) {
        $src = Join-Path $Workspace $f
        if (Test-Path -LiteralPath $src) {
            Copy-Item -LiteralPath $src -Destination (Join-Path $dest $f) -Force
            Write-Host "  已复制: $f -> agents/$AgentDirName/$f"
        }
    }
}

function Show-Diff($dirs) {
    # 对比本地所选技能与远端仓库已有内容（按新结构 agents/<名>/skills）
    $repoSkillsDir = Join-Path $RepoDir ("agents\" + $AgentDirName + "\skills")
    $repoExisting = @()
    if (Test-Path -LiteralPath $repoSkillsDir) {
        $repoExisting = Get-ChildItem -LiteralPath $repoSkillsDir -Directory | Select-Object -ExpandProperty Name
    }
    $localNames = @($dirs | ForEach-Object Name)
    $toAdd = @($localNames | Where-Object { $repoExisting -notcontains $_ })
    $toUpd = @($localNames | Where-Object { $repoExisting -contains $_ })
    $repoOnly = @($repoExisting | Where-Object { $localNames -notcontains $_ })
    Write-Host "--- 与 Gitea 远端对比 ---"
    Write-Host ("  新增(远端没有): {0}" -f $(if ($toAdd) { $toAdd -join ', ' } elseif ($Diff) {
    # 仅 -Diff（无 -Names/-All）：对比全部技能与远端，只报告不上传
    $selected = $dirs
} else { '无' }))
    Write-Host ("  更新(覆盖远端): {0}" -f $(if ($toUpd) { $toUpd -join ', ' } elseif ($Diff) {
    # 仅 -Diff（无 -Names/-All）：对比全部技能与远端，只报告不上传
    $selected = $dirs
} else { '无' }))
    if ($repoOnly) { Write-Host ("  远端独有(本次不动): {0}" -f ($repoOnly -join ', ')) }
}

# ---- 主流程 ----
if ($ListAgents) { Show-AgentList; exit 0 }

$dirs = Get-SkillDirs
if (-not $dirs) { throw "未找到任何技能（$SkillsDir 下没有含 SKILL.md 的目录）" }

if ($ListOnly) {
    Write-Host "可选技能清单（共 $($dirs.Count) 个）："
    for ($i = 0; $i -lt $dirs.Count; $i++) {
        Write-Host ("  [{0}] {1}" -f ($i + 1), $dirs[$i].Name)
    }
    exit 0
}

# 1. 确定要上传的技能
$selected = @()
if ($All) {
    $selected = $dirs
} elseif ($Names -ne "") {
    foreach ($n in ($Names -split ',')) {
        $n = $n.Trim()
        if ($n -match '^\d+$') { $selected += Resolve-Selection $n; continue }
        $d = $dirs | Where-Object { $_.Name -ieq $n }
        if (-not $d) { throw "技能 '$n' 不存在，请用 -ListOnly 查看清单" }
        $selected += $d
    }
} elseif ($Diff) {
    # 仅 -Diff（无 -Names/-All）：对比全部技能与远端，只报告不上传
    $selected = $dirs
} else {
    # 交互模式
    Write-Host "可选技能清单（共 $($dirs.Count) 个）："
    for ($i = 0; $i -lt $dirs.Count; $i++) {
        Write-Host ("  [{0}] {1}" -f ($i + 1), $dirs[$i].Name)
    }
    $sel = Read-Host "请输入要上传的技能序号（支持 1,3-5 或 all）"
    if ($sel -match '^(?i)all$') { $selected = $dirs } elseif ($Diff) {
    # 仅 -Diff（无 -Names/-All）：对比全部技能与远端，只报告不上传
    $selected = $dirs
} else { $selected = Resolve-Selection $sel }
}
$selected = @($selected | Sort-Object FullName -Unique)
Write-Host "将上传 $($selected.Count) 个技能: $(($selected | ForEach-Object Name) -join ', ')"

# 2. 准备本地仓库副本
if (-not (Test-Path (Join-Path $RepoDir ".git"))) {
    Write-Host "首次运行，正在 clone 仓库..."
    cmd /c "git clone $RepoUrl `"$RepoDir`" 2>&1"
    if ($LASTEXITCODE -ne 0) { throw "git clone 失败（仓库可能为空或需要认证）" }
} elseif ($Diff) {
    # 仅 -Diff（无 -Names/-All）：对比全部技能与远端，只报告不上传
    $selected = $dirs
} else {
    cmd /c "git -C `"$RepoDir`" pull --rebase 2>&1"
    if ($LASTEXITCODE -ne 0) { Write-Warning "git pull --rebase 失败，继续尝试提交" }
}

# 3. 对比差异（-Diff 单独使用时仅报告不上传）
if ($Diff) {
    Show-Diff $selected
    if (-not $All -and $Names -eq "") {
        Write-Host "(仅 -Diff 模式：只报告差异，未上传。加 -Names 或 -All 执行上传)"
        exit 0
    }
}

# 4. 复制文件
foreach ($d in $selected) { Copy-SkillToRepo $d }
if ($Profile) { Copy-ProfileToRepo }

# 5. 提交推送
git -C $RepoDir add -A
$stamp = Get-Date -Format "yyyy-MM-dd HH:mm"
$skillList = ($selected | ForEach-Object Name) -join ", "
if ($Message -eq "") {
    if ($Bundle) {
        $Message = "上传智能体完整快照: $AgentDirName ($($selected.Count) 个技能 + 配置)"
    } else {
        $Message = "上传技能: $skillList"
        if ($Agent -ne "") { $Message += " [来自 $Agent]" }
        if ($Profile) { $Message += " + 智能体配置" }
        $Message += " ($stamp)"
    }
}
$commitOut = cmd /c "git -C `"$RepoDir`" commit -m `"$Message`" 2>&1"
if ($LASTEXITCODE -ne 0) {
    if ("$commitOut" -match "nothing to commit") {
        Write-Host "没有检测到任何变更，无需推送。"
        exit 0
    }
    Write-Host "$commitOut"
    throw "git commit 失败"
}
Write-Host "已提交: $Message"

cmd /c "git -C `"$RepoDir`" pull --rebase 2>&1"
cmd /c "git -C `"$RepoDir`" push 2>&1"
if ($LASTEXITCODE -ne 0) { throw "git push 失败（请检查凭据/网络，参见 SKILL.md 错误处理）" }

Write-Host ""
Write-Host "✅ 上传完成！请到 $RepoUrl 查看确认。"
