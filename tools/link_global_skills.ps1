# Global skills junction linker: replace physical copies in 4 global libraries with junction links
# Usage: .\tools\link_global_skills.ps1 -DryRun    (preview)
#        .\tools\link_global_skills.ps1            (execute)

param([switch]$DryRun)

$ProjectRoot = "d:\MyProjects\DevProjectTeamSkill"
$SkillsSource = "$ProjectRoot\.trae\skills"
$DocsSource = "$ProjectRoot\docs"
$ToolsSource = "$ProjectRoot\tools"
$SkillIndexSource = "$SkillsSource\SKILL_INDEX.md"

$GlobalLibs = @(
    "$env:USERPROFILE\.trae-cn\skills"
    "$env:USERPROFILE\.config\opencode\skills"
    "$env:USERPROFILE\.workbuddy\skills"
    "$env:USERPROFILE\.copilot\skills"
)

$NonProjectItems = @("git-commit")

# Collect items to link
$items = @()
Get-ChildItem $SkillsSource -Directory | ForEach-Object { $items += [PSCustomObject]@{Name=$_.Name; Source=$_.FullName; Kind="dir"} }
$items += [PSCustomObject]@{Name="docs"; Source=$DocsSource; Kind="dir"}
$items += [PSCustomObject]@{Name="tools"; Source=$ToolsSource; Kind="dir"}
if (Test-Path $SkillIndexSource) { $items += [PSCustomObject]@{Name="SKILL_INDEX.md"; Source=$SkillIndexSource; Kind="file"} }

$mode = if ($DryRun) { " (DRY RUN)" } else { "" }
Write-Host "=== Global Skills Junction Linker$mode ===" -ForegroundColor Cyan
Write-Host "Source: $SkillsSource"
Write-Host "Items:  $($items.Count)"
Write-Host "Libs:   $($GlobalLibs.Count)"
Write-Host ""

foreach ($libPath in $GlobalLibs) {
    if (-not (Test-Path $libPath)) { Write-Host "--- [SKIP] $libPath not found ---`n" -ForegroundColor Yellow; continue }
    Write-Host "--- $libPath ---" -ForegroundColor Cyan

    foreach ($item in $items) {
        if ($item.Name -in $NonProjectItems) { Write-Host "  [KEEP] $($item.Name) (non-project)" -ForegroundColor DarkGray; continue }

        $linkPath = Join-Path $libPath $item.Name

        if (-not (Test-Path $linkPath)) {
            # Not exists -> create new link
            if ($DryRun) { Write-Host "  [NEW] $($item.Name) -> $($item.Source)" -ForegroundColor Green }
            else {
                if ($item.Kind -eq "dir") {
                    New-Item -ItemType Junction -Path $linkPath -Target $item.Source -Force | Out-Null
                } else {
                    New-Item -ItemType HardLink -Path $linkPath -Target $item.Source -Force | Out-Null
                }
                Write-Host "  [NEW] $($item.Name) -> $($item.Source)" -ForegroundColor Green
            }
        } else {
            # Exists - check if already a link
            $isLink = $false
            try { $gi = Get-Item $linkPath -Force; if ($gi.LinkType) { $isLink = $true } } catch {}
            if ($isLink) {
                Write-Host "  [LINKED] $($item.Name) (skip)" -ForegroundColor DarkGray
            } else {
                # Physical copy -> delete and create link
                if ($DryRun) { Write-Host "  [REPLACE] $($item.Name): delete copy -> $($item.Source)" -ForegroundColor Yellow }
                else {
                    Remove-Item -Path $linkPath -Recurse -Force
                    if ($item.Kind -eq "dir") {
                        New-Item -ItemType Junction -Path $linkPath -Target $item.Source -Force | Out-Null
                    } else {
                        New-Item -ItemType HardLink -Path $linkPath -Target $item.Source -Force | Out-Null
                    }
                    Write-Host "  [REPLACE] $($item.Name) -> $($item.Source)" -ForegroundColor Yellow
                }
            }
        }
    }
    Write-Host ""
}

Write-Host "Done." -ForegroundColor Cyan
