#!/usr/bin/env pwsh
# Kimi ClipMon - Minimal tray test

$log = Join-Path $env:USERPROFILE ".kimi-cli\clips\ps-tray.log"
Start-Transcript -Path $log -Force

Write-Host "=== Tray Test Started ==="

try {
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing

    $notify = New-Object System.Windows.Forms.NotifyIcon
    $notify.Icon = [System.Drawing.SystemIcons]::Application
    $notify.Text = "Kimi ClipMon Test"
    $notify.Visible = $true
    Write-Host "Tray icon visible"

    $menu = New-Object System.Windows.Forms.ContextMenuStrip
    $exitItem = $menu.Items.Add("Exit")

    $exitItem.Add_Click({
        Write-Host "Exit clicked"
        $notify.Visible = $false
        $notify.Dispose()
        Stop-Transcript
        Stop-Process -Id $PID -Force
    }.GetNewClosure())

    $notify.ContextMenuStrip = $menu
    Write-Host "Right-click tray icon and select Exit"

    # Message pump via DoEvents
    while ($true) {
        [System.Windows.Forms.Application]::DoEvents()
        Start-Sleep -Milliseconds 100
    }
} catch {
    Write-Host "[ERROR] $_"
    Write-Host $_.ScriptStackTrace
}

Stop-Transcript

