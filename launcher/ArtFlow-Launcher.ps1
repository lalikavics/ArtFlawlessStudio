# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Lalikavics - ArtFlawless Studio
# ArtFlawless Studio launcher: starts ComfyUI in the background, opens the Studio in its own window,
# and stops ComfyUI when that window is closed.
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot            # <install dir>
$Port = 8199
$Url = "http://127.0.0.1:$Port/artflow"
$Portable = Join-Path $Root 'ComfyUI_windows_portable'
$Py = Join-Path $Portable 'python_embeded\python.exe'
$Main = Join-Path $Portable 'ComfyUI\main.py'
$Log = Join-Path $Root 'launcher\comfyui.log'
$EdgeProfile = Join-Path $Root 'edge-profile'

Add-Type -AssemblyName System.Windows.Forms, System.Drawing
# dark window frame for the Studio window (Windows 10 20H1+: dark title bar; Windows 11: exact Studio colours)
try {
    Add-Type -ErrorAction Stop @"
using System; using System.Runtime.InteropServices;
public static class AfDwm {
  [DllImport("dwmapi.dll")] public static extern int DwmSetWindowAttribute(IntPtr h, int a, ref int v, int s);
  [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr after, int x, int y, int cx, int cy, uint f);
}
"@
} catch { }
$script:Darkened = @{}
function Set-DarkFrame([IntPtr]$hwnd) {
    if ($hwnd -eq [IntPtr]::Zero -or -not ('AfDwm' -as [type])) { return }
    $one = 1; $cap = 0x001F1815; $txt = 0x00F0EAE8
    [void][AfDwm]::DwmSetWindowAttribute($hwnd, 20, [ref]$one, 4)   # immersive dark mode
    [void][AfDwm]::DwmSetWindowAttribute($hwnd, 19, [ref]$one, 4)   # same, older Windows 10 builds
    [void][AfDwm]::DwmSetWindowAttribute($hwnd, 35, [ref]$cap, 4)   # caption colour (Windows 11)
    [void][AfDwm]::DwmSetWindowAttribute($hwnd, 34, [ref]$cap, 4)   # border colour (Windows 11)
    [void][AfDwm]::DwmSetWindowAttribute($hwnd, 36, [ref]$txt, 4)   # caption text colour (Windows 11)
    if (-not $script:Darkened.ContainsKey([string]$hwnd)) {
        [void][AfDwm]::SetWindowPos($hwnd, [IntPtr]::Zero, 0, 0, 0, 0, 0x0027)   # SWP_FRAMECHANGED|NOMOVE|NOSIZE|NOZORDER: redraw the frame
        $script:Darkened[[string]$hwnd] = $true
    }
}

function Show-Error($msg) {
    [void][System.Windows.Forms.MessageBox]::Show($msg, 'ArtFlawless Studio', 'OK', 'Error')
}
function Test-Up {
    try { $r = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/system_stats" -UseBasicParsing -TimeoutSec 2; return ($r.StatusCode -eq 200) } catch { return $false }
}
function Find-Edge {
    $c = @(
        (Join-Path ${env:ProgramFiles(x86)} 'Microsoft\Edge\Application\msedge.exe'),
        (Join-Path $env:ProgramFiles 'Microsoft\Edge\Application\msedge.exe'),
        (Join-Path $env:LOCALAPPDATA 'Microsoft\Edge\Application\msedge.exe')
    )
    foreach ($p in $c) { if ($p -and (Test-Path -LiteralPath $p)) { return $p } }
    try { $k = (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe' -ErrorAction Stop).'(default)'; if ($k -and (Test-Path -LiteralPath $k)) { return $k } } catch { }
    return $null
}
function Get-EdgeProcs {
    $needle = $EdgeProfile.ToLowerInvariant()
    @(Get-CimInstance Win32_Process -Filter "Name='msedge.exe'" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -and $_.CommandLine.ToLowerInvariant().Contains($needle) })
}

function Get-EdgeWindows {
    $ids = @(Get-EdgeProcs | ForEach-Object { [int]$_.ProcessId })
    if (-not $ids.Count) { return @() }
    @(Get-Process -Id $ids -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 })
}

if (-not (Test-Path -LiteralPath $Py) -or -not (Test-Path -LiteralPath $Main)) {
    Show-Error "ComfyUI is not installed completely.`nRun the ArtFlawless Studio setup again to repair the installation."
    exit 1
}

# start window: the rounded Studio panel with the logo, a turning ring and the list of what is happening (Splash.ps1)
$Comfy = Join-Path $Portable 'ComfyUI'
. (Join-Path $PSScriptRoot 'Splash.ps1')
$Lang = Get-UiLang $Comfy
$TX = @{
    en = @{ engine = 'Starting the engine…'; engineOk = 'The engine has started'; gpu = 'Detecting the graphics card…'; gpuOk = 'Graphics card: {0}';
            gpuMem = '{0}, {1} GB'; nodes = 'Loading components…'; nodesOne = 'Loading components: {0} ({1}/{2})…'; nodesOk = 'Components loaded ({0})';
            server = 'Starting the server…'; serverOk = 'The server is running'; running = 'The Studio engine is already running';
            win = 'Opening the workspace…'; winOk = 'The workspace is open'; session = 'Restoring your last session…'; sessionOk = 'Ready';
            first = 'The first start can take 1–2 minutes.'; fail = 'Could not start – see launcher\comfyui.log'; failExit = 'The engine stopped while starting' }
    hu = @{ engine = 'A háttérmotor indítása…'; engineOk = 'A háttérmotor elindult'; gpu = 'Videókártya keresése…'; gpuOk = 'Videókártya: {0}';
            gpuMem = '{0}, {1} GB'; nodes = 'Összetevők betöltése…'; nodesOne = 'Összetevők betöltése: {0} ({1}/{2})…'; nodesOk = 'Összetevők betöltve ({0})';
            server = 'A kiszolgáló indul…'; serverOk = 'A kiszolgáló elindult'; running = 'A Studio motorja már fut';
            win = 'A munkafelület megnyitása…'; winOk = 'A munkafelület megnyílt'; session = 'Előző munkamenet betöltése…'; sessionOk = 'Kész';
            first = 'Az első indítás 1–2 percig is eltarthat.'; fail = 'Nem indult el – a részletek: launcher\comfyui.log'; failExit = 'A háttérmotor indulás közben leállt' }
}
function T([string]$k) { $v = $TX[$Lang][$k]; if ($args.Count) { $v = [string]::Format($v, $args) }; return $v }

$form = $null
if (-not (Start-ArtSplash $true)) {
    # the old plain window, when the new one cannot be shown
    $form = New-Object System.Windows.Forms.Form
    $form.Text = 'ArtFlawless Studio'; $form.StartPosition = 'CenterScreen'; $form.FormBorderStyle = 'FixedDialog'
    $form.ControlBox = $false; $form.TopMost = $true; $form.ClientSize = New-Object System.Drawing.Size(360, 90)
    $form.BackColor = [System.Drawing.Color]::FromArgb(21, 22, 25); $form.ForeColor = [System.Drawing.Color]::White
    $lbl = New-Object System.Windows.Forms.Label
    $lbl.Text = 'ArtFlawless Studio is starting...'; $lbl.AutoSize = $false; $lbl.TextAlign = 'MiddleCenter'; $lbl.Dock = 'Fill'
    $lbl.Font = New-Object System.Drawing.Font('Segoe UI', 11)
    $form.Controls.Add($lbl); $form.Show(); [System.Windows.Forms.Application]::DoEvents()
}
function Close-StartWindow { Close-ArtSplash; if ($form) { try { $form.Close() } catch { } } }

# reads what ComfyUI wrote to its log since the last call (the file stays open for writing by ComfyUI)
$script:LogPos = @{}
function Read-LogLines([string]$path) {
    if (-not (Test-Path -LiteralPath $path)) { return @() }
    try {
        $fs = [IO.File]::Open($path, 'Open', 'Read', 'ReadWrite')
        try {
            $pos = [long]$script:LogPos[$path]; if ($fs.Length -lt $pos) { $pos = 0 }
            $fs.Seek($pos, 'Begin') | Out-Null
            $buf = New-Object byte[] ($fs.Length - $pos)
            $n = $fs.Read($buf, 0, $buf.Length)
            $txt = [Text.Encoding]::UTF8.GetString($buf, 0, $n)
            $cut = $txt.LastIndexOf("`n")
            if ($cut -lt 0) { return @() }
            $script:LogPos[$path] = $pos + [Text.Encoding]::UTF8.GetByteCount($txt.Substring(0, $cut + 1))
            return @($txt.Substring(0, $cut).Split("`n") | ForEach-Object { ($_ -replace '\x1b\[[0-9;]*m', '').TrimEnd("`r") })
        } finally { $fs.Dispose() }
    } catch { return @() }
}

# the custom node folders in the order ComfyUI loads them, to say which one is loading
$NodeDirs = @()
try {
    $NodeDirs = @(Get-ChildItem -LiteralPath (Join-Path $Comfy 'custom_nodes') -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -ne '__pycache__' -and $_.Name -notlike '*.disabled' -and $_.Name -notlike '.*' } | Sort-Object Name | ForEach-Object { $_.Name })
} catch { }
function Norm([string]$x) { return ($x.ToLowerInvariant() -replace '[^a-z0-9]', '') }
$NodeKeys = @($NodeDirs | ForEach-Object { Norm $_ })
$FirstFlag = Join-Path $Comfy 'user\artflow-started.txt'

$owned = $null
if (-not (Test-Up)) {
    $cmdArgs = @('-s', ('"' + $Main + '"'), '--windows-standalone-build', '--listen', '127.0.0.1', '--port', "$Port",
        '--input-directory', ('"' + (Join-Path $Root 'input') + '"'), '--output-directory', ('"' + (Join-Path $Root 'output') + '"'),
        '--disable-auto-launch')
    # optional extra ComfyUI arguments, one or more per line in launcher\comfy-args.txt (lines starting with # are ignored),
    # for example --disable-dynamic-vram when a run hangs while loading or encoding
    $ExtraArgs = Join-Path $PSScriptRoot 'comfy-args.txt'
    if (Test-Path -LiteralPath $ExtraArgs) {
        foreach ($ln in [IO.File]::ReadAllLines($ExtraArgs)) {
            $ln = $ln.Trim(); if (-not $ln -or $ln.StartsWith('#')) { continue }
            foreach ($tok in ($ln -split '\s+')) { if ($tok -match '^--?[A-Za-z0-9][A-Za-z0-9\-]*$' -or $tok -match '^[0-9.]+$') { $cmdArgs += $tok } }
        }
    }
    # ComfyUI's dynamic VRAM loading can hang on cards with more than 10 GB when the models almost fit
    # (seen on a 16 GB card with start image + layout reference together), so it is switched off there;
    # on 8 GB cards it works and is faster. "--enable-dynamic-vram" in comfy-args.txt keeps it on.
    if (-not ($cmdArgs -contains '--enable-dynamic-vram') -and -not ($cmdArgs -contains '--disable-dynamic-vram')) {
        $vram = 0; $how = 'not found'
        # 1) nvidia-smi (in System32 with current drivers, or the old NVSMI folder)
        try {
            $smi = $null
            foreach ($c in @((Join-Path $env:SystemRoot 'System32\nvidia-smi.exe'), (Join-Path $env:ProgramFiles 'NVIDIA Corporation\NVSMI\nvidia-smi.exe'))) { if (Test-Path -LiteralPath $c) { $smi = $c; break } }
            if (-not $smi) { $g = Get-Command nvidia-smi.exe -ErrorAction SilentlyContinue; if ($g) { $smi = $g.Source } }
            if ($smi) {
                foreach ($ln in @(& $smi --query-gpu=memory.total --format=csv,noheader,nounits 2>$null)) {
                    $m = 0; if ([int]::TryParse(([string]$ln).Trim(), [ref]$m) -and $m -gt $vram) { $vram = $m; $how = 'nvidia-smi' }
                }
            }
        } catch { }
        # 2) the display driver's registry entry (64-bit memory size in bytes), when nvidia-smi gave nothing
        if ($vram -le 0) {
            try {
                Get-ChildItem 'HKLM:\SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}' -ErrorAction SilentlyContinue | ForEach-Object {
                    $p = Get-ItemProperty -LiteralPath $_.PSPath -ErrorAction SilentlyContinue
                    if ($p -and ([string]$p.DriverDesc) -match 'NVIDIA') {
                        $b = $p.'HardwareInformation.qwMemorySize'
                        if ($b) { $mb = [int]([int64]$b / 1MB); if ($mb -gt $vram) { $vram = $mb; $how = 'registry' } }
                    }
                }
            } catch { }
        }
        $dyn = 'on'
        if ($vram -gt 10240) { $cmdArgs += '--disable-dynamic-vram'; $dyn = 'off' }
        try { Add-Content -LiteralPath (Join-Path $PSScriptRoot 'launcher.log') -Value ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + "  VRAM $vram MB ($how), dynamic VRAM $dyn") -Encoding UTF8 } catch { }
    }
    # keep the log of the previous session (for example after a hang and a restart) next to the new one
    foreach ($x in @($Log, ($Log + '.err'))) {
        if (Test-Path -LiteralPath $x) { try { Move-Item -LiteralPath $x -Destination ($x -replace 'comfyui\.log', 'comfyui.prev.log') -Force } catch { } }
    }
    Splash-Step (T 'engine')
    $owned = Start-Process -FilePath $Py -ArgumentList $cmdArgs -WorkingDirectory $Portable -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput $Log -RedirectStandardError ($Log + '.err')
    Start-Sleep -Milliseconds 400
    Splash-Done (T 'engineOk'); Splash-Step (T 'gpu')
    if (-not (Test-Path -LiteralPath $FirstFlag)) { Splash-Note (T 'first') }
    $stage = 'gpu'; $vramMb = 0; $nodeCount = 0; $nodeIdx = 0; $started = Get-Date; $noted = $false
    $deadline = (Get-Date).AddMinutes(6)
    while ($true) {
        foreach ($ln in @(Read-LogLines ($Log + '.err')) + @(Read-LogLines $Log)) {
            if ($ln -match 'Total VRAM (\d+) MB') { $vramMb = [int]$Matches[1] }
            if ($stage -eq 'gpu' -and $ln -match 'Device: \S+ (.+?)( : \S+)?\s*$') {
                $name = $Matches[1].Trim()
                if ($vramMb -gt 0) { $name = T 'gpuMem' $name ([math]::Round($vramMb / 1024)) }
                Splash-Done (T 'gpuOk' $name); Splash-Step (T 'nodes'); $stage = 'nodes'; continue
            }
            if ($stage -eq 'nodes') {
                if ($ln -match 'Import times for custom nodes') { $stage = 'times'; continue }
                $nl = Norm $ln
                for ($i = $nodeIdx; $i -lt $NodeKeys.Count; $i++) {
                    if ($NodeKeys[$i].Length -ge 5 -and $nl.Contains($NodeKeys[$i])) { $nodeIdx = $i + 1; Splash-Update (T 'nodesOne' $NodeDirs[$i] $nodeIdx $NodeDirs.Count); break }
                }
                continue
            }
            if ($stage -eq 'times') {
                if ($ln -match 'seconds( \(IMPORT FAILED\))?: .*custom_nodes[\\/](.+)$') { if ($Matches[2] -notmatch '\.py$') { $nodeCount++ }; continue }
                Splash-Done (T 'nodesOk' $nodeCount); Splash-Step (T 'server'); $stage = 'server'
            }
            if ($stage -eq 'server' -and $ln -match 'To see the GUI go to|Starting server') { $stage = 'up' }
        }
        if (Test-Up) { break }
        if (-not $noted -and ((Get-Date) - $started).TotalSeconds -gt 25) { $noted = $true; if (Test-Path -LiteralPath $FirstFlag) { Splash-Note (T 'first') } }
        if ($owned.HasExited -or (Get-Date) -gt $deadline) {
            if ($owned.HasExited) { Splash-Error (T 'failExit') }
            Splash-Error (T 'fail')
            $tail = ''
            try { $tail = (Get-Content -LiteralPath ($Log + '.err') -Tail 12 -ErrorAction SilentlyContinue) -join "`n" } catch { }
            if ($script:SplashOk) { [void](Splash-Ask ("ComfyUI did not start.`n`nLog: $Log`n`n$tail")) } else { Show-Error ("ComfyUI did not start.`n`nLog: $Log`n`n$tail") }
            Close-StartWindow
            if (-not $owned.HasExited) { & taskkill.exe /PID $owned.Id /T /F | Out-Null }
            exit 1
        }
        if ($form) { [System.Windows.Forms.Application]::DoEvents() }
        Start-Sleep -Milliseconds 250
    }
    if ($stage -in @('gpu', 'nodes')) { Splash-Done $null }
    if ($stage -ne 'server' -and $stage -ne 'up') { Splash-Step (T 'server') }
    Splash-Done (T 'serverOk')
    try { [IO.File]::WriteAllText($FirstFlag, (Get-Date -Format 's')) } catch { }
} else {
    Splash-Done (T 'running')
}

function Stop-Comfy { if ($owned -and -not $owned.HasExited) { & taskkill.exe /PID $owned.Id /T /F | Out-Null } }

# frameless Studio window (WebView2); falls back to an Edge app window when WebView2 is not available
$HostExe = Join-Path $PSScriptRoot 'webview2\ArtFlawlessHost.exe'
$HostSrc = Join-Path $PSScriptRoot 'ArtFlawlessHost.cs'
if ((Test-Path -LiteralPath $HostSrc) -and (-not (Test-Path -LiteralPath $HostExe) -or (Get-Item -LiteralPath $HostSrc).LastWriteTimeUtc -gt (Get-Item -LiteralPath $HostExe).LastWriteTimeUtc -or
    -not (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'webview2\host.build')))) {
    try { & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'Build-Host.ps1') *> (Join-Path $PSScriptRoot 'build-host.log') } catch { }
}
if (Test-Path -LiteralPath $HostExe) {
    $data = Join-Path $Root 'studio-window'
    $readyFile = Join-Path $Comfy 'user\artflow-ready.txt'
    try { if (Test-Path -LiteralPath $readyFile) { Remove-Item -LiteralPath $readyFile -Force } } catch { }
    Splash-Step (T 'win')
    $hp = Start-Process -FilePath $HostExe -ArgumentList @($Url, ('"' + $data + '"'), ('"' + (Join-Path $PSScriptRoot 'artflow.ico') + '"')) -PassThru
    $null = $hp.Handle   # keeps the exit code readable after the process ends (Windows PowerShell quirk)
    # the start window stays until the Studio page has loaded (it writes artflow-ready.txt), at most ~45 s
    $until = (Get-Date).AddSeconds(45); $winSeen = $false
    while ((Get-Date) -lt $until -and -not $hp.HasExited) {
        if (-not $winSeen) { try { $hp.Refresh(); if ($hp.MainWindowHandle -ne [IntPtr]::Zero) { $winSeen = $true; Splash-Done (T 'winOk'); Splash-Step (T 'session') } } catch { } }
        if (Test-Path -LiteralPath $readyFile) { break }
        Start-Sleep -Milliseconds 200
    }
    if (-not $hp.HasExited) { if (-not $winSeen) { Splash-Done (T 'winOk'); Splash-Step (T 'session') }; Splash-Done (T 'sessionOk'); Start-Sleep -Milliseconds 1850 }   # a moment to read what happened
    Close-StartWindow
    $hp.WaitForExit()
    if ($hp.ExitCode -ne 3 -and $hp.ExitCode -ne 4) { Stop-Comfy; exit 0 }
}

Close-StartWindow
$edge = Find-Edge
if ($edge) {
    New-Item -ItemType Directory -Force -Path $EdgeProfile | Out-Null
    Start-Process -FilePath $edge -ArgumentList @("--app=$Url", ('--user-data-dir="' + $EdgeProfile + '"'), '--window-size=1500,950', '--no-first-run', '--no-default-browser-check') | Out-Null
    # Edge can keep background processes alive after its window is closed, so watch for the WINDOW, not the processes
    $seen = $false
    $until = (Get-Date).AddSeconds(60)
    while ((Get-Date) -lt $until -and -not $seen) { Start-Sleep -Milliseconds 300; $wins = @(Get-EdgeWindows); if ($wins.Count -gt 0) { $seen = $true; foreach ($w in $wins) { Set-DarkFrame $w.MainWindowHandle } } }
    if ($seen) { while ($true) { $wins = @(Get-EdgeWindows); if ($wins.Count -eq 0) { break }; foreach ($w in $wins) { Set-DarkFrame $w.MainWindowHandle }; Start-Sleep -Milliseconds 1500 } }
    else { while ((Get-EdgeProcs).Count -gt 0) { Start-Sleep -Seconds 2 } }
    foreach ($p in (Get-EdgeProcs)) { & taskkill.exe /PID $p.ProcessId /F 2>$null | Out-Null }
    Stop-Comfy
    exit 0
}

# no Edge: default browser + a small window that keeps ComfyUI alive until you press Stop
Start-Process $Url
$f2 = New-Object System.Windows.Forms.Form
$f2.Text = 'ArtFlawless Studio'; $f2.StartPosition = 'CenterScreen'; $f2.ClientSize = New-Object System.Drawing.Size(380, 120); $f2.TopMost = $true
$l2 = New-Object System.Windows.Forms.Label
$l2.Text = "ArtFlawless Studio is running in your browser:`n$Url`n`nClose this window to stop it."
$l2.AutoSize = $false; $l2.Dock = 'Fill'; $l2.TextAlign = 'MiddleCenter'
$f2.Controls.Add($l2)
[void]$f2.ShowDialog()
Stop-Comfy
