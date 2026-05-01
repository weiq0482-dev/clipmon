#!/usr/bin/env pwsh
# Kimi ClipMon - 一键配置开机自启
# 运行后会创建一个快捷方式到 Windows 启动文件夹

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$StartPsPath = Join-Path $ScriptDir "start.ps1"

if (-not (Test-Path $StartPsPath)) {
    Write-Host "错误：找不到 start.ps1，请确认它在同一目录" -ForegroundColor Red
    exit 1
}

# Windows 启动文件夹路径
$StartupPath = [Environment]::GetFolderPath("Startup")
$ShortcutPath = Join-Path $StartupPath "KimiClipMon.lnk"

# 创建快捷方式
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "powershell.exe"
$Shortcut.Arguments = "-WindowStyle Hidden -ExecutionPolicy Bypass -File `"$StartPsPath`""
$Shortcut.WorkingDirectory = $ScriptDir
$Shortcut.Description = "Kimi ClipMon - 目录监视截图守护"
$Shortcut.IconLocation = "shell32.dll,14"
$Shortcut.Save()

Write-Host "✅ Kimi ClipMon 已添加到开机启动项" -ForegroundColor Green
Write-Host ""
Write-Host "快捷方式位置: $ShortcutPath"
Write-Host "启动脚本:    $StartPsPath"
Write-Host ""
Write-Host "你可以："
Write-Host "  1. 立即双击上面快捷方式测试启动"
Write-Host "  2. 重启电脑后会自动在托盘运行"
Write-Host ""
Write-Host "如需取消自启，删除以下文件即可：" -ForegroundColor Yellow
Write-Host "  $ShortcutPath"
