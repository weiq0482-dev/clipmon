#!/usr/bin/env pwsh
# Kimi ClipMon Launcher - Zero Clipboard Interference
# 原则：程序完全不碰系统剪贴板，用户手动查看编号

$LogFile = Join-Path $env:USERPROFILE ".kimi-cli\clips\ps-tray.log"
Start-Transcript -Path $LogFile -Force -ErrorAction SilentlyContinue
Write-Host "=== start.ps1 started at $(Get-Date) ==="

try {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $DaemonPath = Join-Path $ScriptDir "daemon.py"
    Write-Host "ScriptDir: $ScriptDir"

    if (-not (Test-Path $DaemonPath)) {
        throw "daemon.py not found"
    }

    $clipsDir = Join-Path (Join-Path $env:USERPROFILE ".kimi-cli") "clips"
    [void](New-Item -ItemType Directory -Path $clipsDir -Force)

    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    Write-Host "WinForms OK"

    $notify = New-Object System.Windows.Forms.NotifyIcon
    $notify.Icon = [System.Drawing.SystemIcons]::Application
    $notify.Text = "Kimi ClipMon - Right click for menu"
    $notify.Visible = $true
    Write-Host "NotifyIcon OK"

    # ── Menu ──
    $menu = New-Object System.Windows.Forms.ContextMenuStrip

    # 历史编号子菜单（只显示，不复制）
    $historyMenu = New-Object System.Windows.Forms.ToolStripMenuItem "Recent tags (&H)"
    $menu.Items.Add($historyMenu)

    $openFolder = $menu.Items.Add("Open clips folder (&O)")
    $viewLatest = $menu.Items.Add("View latest list (&L)")
    $cleanupItem = $menu.Items.Add("Cleanup old clips (&D)")
    [void]$menu.Items.Add("-")
    $exitItem = $menu.Items.Add("Exit (&X)")

    function RefreshHistoryMenu {
        $historyMenu.DropDownItems.Clear()
        $manifest = Join-Path $clipsDir "manifest.jsonl"
        if (Test-Path $manifest) {
            $lines = Get-Content $manifest -Tail 5
            if ($lines) {
                [array]::Reverse($lines)
                foreach ($line in $lines) {
                    try {
                        $obj = $line | ConvertFrom-Json
                        $tag = $obj.id
                        $fname = $obj.filename
                        $label = "$tag  $fname"
                        $item = $historyMenu.DropDownItems.Add($label)
                        $item.Tag = $tag
                        $item.Add_Click({
                            $t = $this.Tag
                            [System.Windows.Forms.Clipboard]::SetText($t)
                            $notify.BalloonTipTitle = "Kimi ClipMon"
                            $notify.BalloonTipText = "Copied $t to clipboard"
                            $notify.ShowBalloonTip(1500)
                        }.GetNewClosure())
                    } catch {}
                }
            }
        }
        if ($historyMenu.DropDownItems.Count -eq 0) {
            [void]$historyMenu.DropDownItems.Add("(no clips yet)")
        }
    }

    RefreshHistoryMenu

    $openFolder.Add_Click({
        Start-Process explorer.exe "`"$clipsDir`""
    }.GetNewClosure())

    $viewLatest.Add_Click({
        $latestMd = Join-Path $clipsDir "latest.md"
        if (Test-Path $latestMd) { Start-Process notepad.exe "`"$latestMd`"" }
        else { [System.Windows.Forms.MessageBox]::Show("No clips yet", "Kimi ClipMon") }
    }.GetNewClosure())

    $cleanupItem.Add_Click({
        try {
            $psi = New-Object System.Diagnostics.ProcessStartInfo
            $psi.FileName = "python"
            $psi.Arguments = "`"$DaemonPath`" --cleanup"
            $psi.CreateNoWindow = $true
            $psi.UseShellExecute = $false
            $psi.RedirectStandardOutput = $true
            $proc = [System.Diagnostics.Process]::Start($psi)
            $out = $proc.StandardOutput.ReadToEnd()
            $proc.WaitForExit()
            $msg = if ($out.Trim()) { $out.Trim() } else { "Cleanup done" }
            [System.Windows.Forms.MessageBox]::Show($msg, "Kimi ClipMon")
            RefreshHistoryMenu
        } catch {
            [System.Windows.Forms.MessageBox]::Show("Cleanup failed: $_", "Kimi ClipMon", "OK", "Error")
        }
    }.GetNewClosure())

    $exitItem.Add_Click({
        $notify.Visible = $false
        $notify.Dispose()
        if ($global:pythonProcess -and -not $global:pythonProcess.HasExited) {
            Stop-Process -Id $global:pythonProcess.Id -Force -ErrorAction SilentlyContinue
        }
        Stop-Transcript
        Stop-Process -Id $PID -Force
    }.GetNewClosure())

    # 点击气泡通知 = 复制编号到剪贴板
    $notify.Add_BalloonTipClicked({
        if ($global:lastTag) {
            [System.Windows.Forms.Clipboard]::SetText($global:lastTag)
            $notify.BalloonTipTitle = "Kimi ClipMon"
            $notify.BalloonTipText = "Copied $global:lastTag to clipboard"
            $notify.ShowBalloonTip(1500)
        }
    })

    $notify.ContextMenuStrip = $menu

    # 左键单击托盘图标 = 打开 latest.md（查看编号列表）
    $notify.Add_MouseClick({
        if ($_.Button -eq [System.Windows.Forms.MouseButtons]::Left) {
            $viewLatest.PerformClick()
        }
    }.GetNewClosure())

    # ── Start Python daemon ──
    Write-Host "Starting Python daemon..."
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "python"
    $psi.Arguments = "`"$DaemonPath`""
    $psi.CreateNoWindow = $true
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $global:pythonProcess = [System.Diagnostics.Process]::Start($psi)
    Write-Host "Python PID: $($global:pythonProcess.Id)"

    # ── File watcher ──
    $notifyFile = Join-Path $clipsDir ".notify"
    $watcher = New-Object System.IO.FileSystemWatcher
    $watcher.Path = $clipsDir
    $watcher.Filter = ".notify"
    $watcher.NotifyFilter = [System.IO.NotifyFilters]::LastWrite

    $global:notifyJob = Register-ObjectEvent -InputObject $watcher -EventName Changed -Action {
        try {
            $content = Get-Content $notifyFile -Raw -ErrorAction SilentlyContinue
            if ($content) {
                $parts = $content.Trim() -split "\s+", 2
                $tag = $parts[0]
                $fname = if ($parts.Length -gt 1) { $parts[1] } else { "" }
                $global:lastTag = $tag
                $notify.BalloonTipTitle = "Kimi ClipMon"
                $notify.BalloonTipText = "Saved $tag`n$fname`nClick to copy"
                $notify.ShowBalloonTip(2000)
                RefreshHistoryMenu
            }
        } catch {}
    }
    $watcher.EnableRaisingEvents = $true
    Write-Host "Watcher OK"

    # ── Message pump via DoEvents ──
    Write-Host "Running message loop..."
    while ($true) {
        [System.Windows.Forms.Application]::DoEvents()
        Start-Sleep -Milliseconds 100
    }

} catch {
    Write-Host "[FATAL] $_"
    Write-Host "[STACK] $($_.ScriptStackTrace)"
    Stop-Transcript
    [System.Windows.Forms.MessageBox]::Show("Failed: $_`n`nLog: $LogFile", "Kimi ClipMon", "OK", "Error")
}
