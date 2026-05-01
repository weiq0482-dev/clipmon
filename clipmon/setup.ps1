# Kimi ClipMon Setup
# One-click installer: check env, install deps, create shortcuts, auto-start

Add-Type -AssemblyName System.Windows.Forms

$InstallDir = Join-Path $env:LOCALAPPDATA "KimiClipMon"
$StartupDir = [Environment]::GetFolderPath("Startup")
$DesktopDir = [Environment]::GetFolderPath("Desktop")
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Show-Error($msg) {
    [System.Windows.Forms.MessageBox]::Show($msg, "ClipMon Setup", "OK", "Error")
}

function Show-Info($msg) {
    [System.Windows.Forms.MessageBox]::Show($msg, "ClipMon Setup", "OK", "Information")
}

# 1. Check Python
Write-Host "Checking Python..."
try {
    $pyVer = python --version 2>&1
    Write-Host "OK: $pyVer"
} catch {
    Show-Error "Python not found. Please install Python 3.8+ first.`nhttps://www.python.org/downloads/"
    exit 1
}

# 2. Check/Install Pillow
Write-Host "Checking Pillow..."
try {
    python -c "from PIL import Image" 2>$null
    Write-Host "OK: Pillow already installed"
} catch {
    Write-Host "Installing Pillow (this may take a minute)..."
    python -m pip install Pillow --quiet 2>&1 | Out-Null
    try {
        python -c "from PIL import Image" 2>$null
        Write-Host "OK: Pillow installed"
    } catch {
        Show-Error "Failed to install Pillow. Please run: pip install Pillow"
        exit 1
    }
}

# 3. Create install directory
Write-Host "Installing to $InstallDir..."
[void](New-Item -ItemType Directory -Path $InstallDir -Force)

# 4. Copy files
$files = @("daemon.py", "start.ps1", "run.bat", "run-debug.bat", "README.md", "LICENSE")
foreach ($f in $files) {
    $src = Join-Path $ScriptDir $f
    if (Test-Path $src) {
        Copy-Item $src $InstallDir -Force
    }
}

# 5. Create desktop shortcut
$Wsh = New-Object -ComObject WScript.Shell
$desk = $Wsh.CreateShortcut("$DesktopDir\Kimi ClipMon.lnk")
$desk.TargetPath = "powershell.exe"
$desk.Arguments = "-WindowStyle Hidden -ExecutionPolicy Bypass -File `"$InstallDir\start.ps1`""
$desk.WorkingDirectory = $InstallDir
$desk.IconLocation = "shell32.dll,14"
$desk.Description = "Kimi ClipMon - Screenshot tag tool"
$desk.Save()

# 6. Create startup shortcut (auto-start on boot)
$start = $Wsh.CreateShortcut("$StartupDir\KimiClipMon.lnk")
$start.TargetPath = "powershell.exe"
$start.Arguments = "-WindowStyle Hidden -ExecutionPolicy Bypass -File `"$InstallDir\start.ps1`""
$start.WorkingDirectory = $InstallDir
$start.IconLocation = "shell32.dll,14"
$start.Description = "Kimi ClipMon - Auto start"
$start.Save()

Write-Host "Installation complete!"

# 7. Start program
Write-Host "Starting Kimi ClipMon..."
Start-Process powershell -ArgumentList "-WindowStyle Hidden -ExecutionPolicy Bypass -File `"$InstallDir\start.ps1`"" -WindowStyle Hidden

Show-Info "Kimi ClipMon installed!`n`nInstall dir: $InstallDir`nDesktop shortcut: created`nAuto-start on boot: enabled`n`nRight-click tray icon for menu.`nClick balloon to copy @N tag."
