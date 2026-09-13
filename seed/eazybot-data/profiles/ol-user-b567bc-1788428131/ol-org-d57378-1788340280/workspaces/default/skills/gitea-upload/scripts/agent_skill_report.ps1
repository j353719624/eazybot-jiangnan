# agent_skill_report.ps1 - 智能体技能审计报告
# 功能：
#   1. 扫描所有智能体工作空间，列出各自拥有的技能
#   2. 计算技能全池，指出每个智能体"缺少"哪些技能
#   3. 对比 Gitea 本地仓库副本，指出哪些技能从未上传
# 用法：powershell -File agent_skill_report.ps1
param()
$ErrorActionPreference = "Stop"

$SkillRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSCommandPath))  # ...\workspaces\<id>\skills
$Workspace = Split-Path -Parent $SkillRoot                                                # ...\workspaces\<id>
$WsRoot    = Split-Path -Parent $Workspace                                                # ...\workspaces
$RepoDir   = Join-Path $Workspace "gitea-skills-repo"

# ---- 收集各智能体技能 ----
$agents = @()
Get-ChildItem -LiteralPath $WsRoot -Directory | ForEach-Object {
    $sk = Join-Path $_.FullName "skills"
    $list = @()
    if (Test-Path -LiteralPath $sk) {
        $list = Get-ChildItem -LiteralPath $sk -Directory |
            Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName "SKILL.md") } |
            Select-Object -ExpandProperty Name | Sort-Object
    }
    $agents += [PSCustomObject]@{ Id = $_.Name; Skills = $list }
}
if (-not $agents) { throw "未在 $WsRoot 下发现任何智能体工作空间" }

$allSkills = @($agents | ForEach-Object { $_.Skills } | Sort-Object -Unique)

# ---- 远端仓库副本已有技能（新结构：agents/<名>/skills/ 汇总去重）----
$repoSkills = @()
$repoAgentsDir = Join-Path $RepoDir "agents"
if (Test-Path -LiteralPath $repoAgentsDir) {
    $repoSkills = Get-ChildItem -LiteralPath $repoAgentsDir -Directory | ForEach-Object {
        $sk = Join-Path $_.FullName "skills"
        if (Test-Path -LiteralPath $sk) {
            Get-ChildItem -LiteralPath $sk -Directory | Select-Object -ExpandProperty Name
        }
    } | Sort-Object -Unique
}

Write-Host "======== 智能体技能审计报告 ======"
Write-Host ("智能体总数: {0}    技能全池: {1} 个    仓库副本(Gitea)已有: {2} 个" -f $agents.Count, $allSkills.Count, $repoSkills.Count)

# ---- 每个智能体的缺失清单 ----
foreach ($a in $agents) {
    $missing = @($allSkills | Where-Object { $a.Skills -notcontains $_ })
    Write-Host ""
    Write-Host ("◆ {0}：拥有 {1} 个技能" -f $a.Id, $a.Skills.Count)
    if ($missing.Count -gt 0) {
        Write-Host ("  缺少 {0} 个: {1}" -f $missing.Count, ($missing -join ', '))
    } else {
        Write-Host "  无缺失（拥有全部技能）"
    }
}

# ---- 技能分布矩阵 ----
Write-Host ""
Write-Host "==== 技能分布矩阵（√=拥有  ·=缺少  *未上传=Gitea 仓库中没有）===="
for ($i = 0; $i -lt $agents.Count; $i++) { Write-Host ("  列{0} = {1}" -f ($i + 1), $agents[$i].Id) }
Write-Host ""
foreach ($s in $allSkills) {
    $row = ($agents | ForEach-Object { if ($_.Skills -contains $s) { "√" } else { "·" } }) -join "  "
    $mark = if ($repoSkills -notcontains $s) { "  *未上传*" } else { "" }
    Write-Host ("  {0,-26} {1}{2}" -f $s, $row, $mark)
}

# ---- 未上传汇总 ----
$notUploaded = @($allSkills | Where-Object { $repoSkills -notcontains $_ })
Write-Host ""
if ($notUploaded.Count -gt 0) {
    Write-Host ("⚠ 以下 {0} 个技能尚未上传到 Gitea：" -f $notUploaded.Count)
    foreach ($s in $notUploaded) {
        $owners = ($agents | Where-Object { $_.Skills -contains $s } | ForEach-Object Id) -join ', '
        Write-Host ("  - {0}  (存在于: {1})" -f $s, $owners)
    }
} else {
    Write-Host "✅ 所有技能均已上传到 Gitea 仓库副本。"
}
