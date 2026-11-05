# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Lalikavics - ArtFlawless Studio
# ArtFlawless Studio - component installer (run by the setup wizard; can be re-run safely to resume/repair).
# Downloads ComfyUI (portable), the custom nodes and the models from their original sources.
# It runs without a console: what it does, and how far each download is, shows in the ArtFlawless start window (Splash.ps1);
# everything is also written to launcher\install.log.
param([Parameter(Mandatory = $true)][string]$InstallDir, [string]$Lang = 'en')

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# ------------------------------------------------------------------ settings
$ComfyTag = 'v0.38.0'
$Port = 8199
$Tools = Join-Path $InstallDir 'launcher\tools'
$Payload = Join-Path $InstallDir 'launcher\payload'
$Portable = Join-Path $InstallDir 'ComfyUI_windows_portable'
$Comfy = Join-Path $Portable 'ComfyUI'
$Py = Join-Path $Portable 'python_embeded\python.exe'
$Models = Join-Path $Comfy 'models'
$Nodes = Join-Path $Comfy 'custom_nodes'
$Curl = Join-Path $env:SystemRoot 'System32\curl.exe'
$Warnings = New-Object System.Collections.Generic.List[string]

New-Item -ItemType Directory -Force -Path $Tools, (Join-Path $InstallDir 'input'), (Join-Path $InstallDir 'output') | Out-Null
try { Start-Transcript -Path (Join-Path $InstallDir 'launcher\install.log') -Append | Out-Null } catch { }

# ------------------------------------------------------------------ the window
. (Join-Path $InstallDir 'launcher\Splash.ps1')
if ($Lang -notin @('hu', 'en')) { $Lang = 'en' }
$TX = @{
    en = @{ title = 'ArtFlawless Studio Setup'; s0 = 'Checking this computer…'; gpu = 'Graphics card: {0}, {1} GB, driver {2}'; s1 = 'ComfyUI {0}';
            s2 = 'Components'; s3 = 'ArtFlawless Studio'; s4 = 'Models (about 25 GB)'; s5 = 'Base LoRA (Civitai)'; s6 = 'Finishing…';
            have = '{0} – already here'; dl = '{0}'; dlp = '{0}: {1} / {2} ({3}%) · {4}/s'; dlpn = '{0}: {1} · {2}/s'; dlok = '{0} – downloaded ({1})';
            unpack = 'Unpacking ComfyUI… {0}%'; unpackOk = 'ComfyUI unpacked'; comfyHave = 'ComfyUI is already installed';
            pip = 'Python packages: {0}…'; node = '({1}/{2}) {0}'; nodeHave = '({1}/{2}) {0} – already installed'; nodeOk = '({1}/{2}) {0} – installed';
            model = '({1}/{2}) {0}'; studioOk = 'Studio files in place'; check = 'Content check (NudeNet)…'; checkOk = 'Content check is ready';
            mirror = 'trying the mirror…'; lora = 'Hands + Feet + skin LoRA'; loraOk = 'Base LoRA is in place'; loraSkip = 'Base LoRA skipped (it can be added later)';
            host = 'Preparing the Studio window…'; hostOk = 'Studio window ready'; warn = 'Warning: {0}'; allOk = 'Everything is installed';
            warnN = 'Finished with {0} warning(s)'; stop = 'Setup stopped: {0}'; resume = 'You can close it now: running the setup again continues where it stopped.';
            loraAsk = "The base LoRA needs a free Civitai login, so it cannot be downloaded automatically.`n`n1. Your browser opens the download page: log in to Civitai and download the file.`n2. Save it into the folder that opens:`n   {0}`n   (or move it there from Downloads).`n3. Then press OK.`n`nPress Cancel to skip it - the Studio works without the LoRA.";
            sumWarn = "Setup finished with {0} warning(s):`n`n{1}`n`nThe Studio lists anything missing when it starts, and the setup can be run again to retry.";
            sumMiss = "The base model files are missing:`n{0}`n`nRun the setup again to continue the download." }
    hu = @{ title = 'ArtFlawless Studio telepítő'; s0 = 'A számítógép ellenőrzése…'; gpu = 'Videókártya: {0}, {1} GB, illesztőprogram {2}'; s1 = 'ComfyUI {0}';
            s2 = 'Összetevők'; s3 = 'ArtFlawless Studio'; s4 = 'Modellek (kb. 25 GB)'; s5 = 'Alap LoRA (Civitai)'; s6 = 'Befejezés…';
            have = '{0} – már megvan'; dl = '{0}'; dlp = '{0}: {1} / {2} ({3}%) · {4}/s'; dlpn = '{0}: {1} · {2}/s'; dlok = '{0} – letöltve ({1})';
            unpack = 'A ComfyUI kicsomagolása… {0}%'; unpackOk = 'A ComfyUI kicsomagolva'; comfyHave = 'A ComfyUI már telepítve van';
            pip = 'Python-csomagok: {0}…'; node = '({1}/{2}) {0}'; nodeHave = '({1}/{2}) {0} – már telepítve'; nodeOk = '({1}/{2}) {0} – telepítve';
            model = '({1}/{2}) {0}'; studioOk = 'A Studio fájljai a helyükön'; check = 'Tartalomellenőrzés (NudeNet)…'; checkOk = 'A tartalomellenőrzés kész';
            mirror = 'a tükörszerver próbálása…'; lora = 'Hands + Feet + skin LoRA'; loraOk = 'Az alap LoRA a helyén'; loraSkip = 'Az alap LoRA kimaradt (később is hozzáadható)';
            host = 'A Studio ablakának előkészítése…'; hostOk = 'A Studio ablaka kész'; warn = 'Figyelmeztetés: {0}'; allOk = 'Minden telepítve';
            warnN = 'Kész, {0} figyelmeztetéssel'; stop = 'A telepítés leállt: {0}'; resume = 'Bezárhatod: a telepítő újbóli futtatása ott folytatja, ahol abbahagyta.';
            loraAsk = "Az alap LoRA letöltéséhez ingyenes Civitai-belépés kell, ezért nem tölthető le automatikusan.`n`n1. A böngésző megnyitja a letöltési oldalt: lépj be a Civitaira, és töltsd le a fájlt.`n2. Mentsd a megnyíló mappába:`n   {0}`n   (vagy helyezd át oda a Letöltések mappából).`n3. Utána nyomd meg az OK gombot.`n`nA Mégse gombbal kihagyhatod - a Studio a LoRA nélkül is működik.";
            sumWarn = "A telepítés {0} figyelmeztetéssel fejeződött be:`n`n{1}`n`nA Studio induláskor jelzi, ha valami hiányzik, és a telepítő újra futtatható.";
            sumMiss = "Hiányoznak az alapmodell fájljai:`n{0}`n`nFuttasd újra a telepítőt a letöltés folytatásához." }
}
function T([string]$k) { $v = $TX[$Lang][$k]; if ($args.Count) { $v = [string]::Format($v, $args) }; return $v }
if (-not (Start-ArtSplash $false)) { Show-Console }
if ($script:SplashOk) { [ArtSplash]::SetTitle((T 'title')) }

trap {
    Write-Host ''
    Write-Host ('INSTALLATION STOPPED: ' + $_.Exception.Message) -ForegroundColor Red
    try { Stop-Transcript | Out-Null } catch { }
    Splash-Error (T 'stop' $_.Exception.Message)
    [void](Splash-Ask ((T 'stop' $_.Exception.Message) + "`n`n" + (T 'resume') + "`n`n" + (Join-Path $InstallDir 'launcher\install.log')))
    Close-ArtSplash
    exit 1
}

function Step($n, $text) { Write-Host ''; Write-Host ("[{0}] {1}" -f $n, $text) -ForegroundColor Cyan; Splash-Step $text }
function Warn($text) { $Warnings.Add($text); Write-Host ("  WARNING: " + $text) -ForegroundColor Yellow; Splash-Fail (T 'warn' $text) }

# size-checked, resumable download (curl.exe ships with Windows 10 1803+)
# the size of the file behind the URL (after the redirects), 0 when the server does not say
function Get-RemoteSize([string]$Url) {
    $len = 0
    try { foreach ($l in @(& $Curl -sIL --max-time 25 $Url 2>$null)) { if ($l -match '^\s*content-length:\s*(\d+)') { $len = [long]$Matches[1] } } } catch { }
    return $len
}
# curl runs hidden; the window shows how far it is: "Label: 3.2 / 12.3 GB (26%) · 18 MB/s"
function Invoke-Download([string]$Url, [string]$Part, [string]$Text, [long]$Total) {
    $a = @('-L', '--fail', '--retry', '5', '--retry-delay', '3', '-C', '-', '-s', '-S', '-o', ('"' + $Part + '"'), ('"' + $Url + '"'))
    $p = Start-Process -FilePath $Curl -ArgumentList $a -WindowStyle Hidden -PassThru
    $null = $p.Handle
    $lastB = -1L; $lastT = Get-Date; $speed = 0.0
    while (-not $p.HasExited) {
        Start-Sleep -Milliseconds 500
        $b = 0L; try { if (Test-Path -LiteralPath $Part) { $b = (Get-Item -LiteralPath $Part).Length } } catch { }
        $now = Get-Date; $dt = ($now - $lastT).TotalSeconds
        if ($lastB -ge 0 -and $dt -gt 0) { $speed = 0.7 * $speed + 0.3 * [math]::Max(0, ($b - $lastB) / $dt) }
        $lastB = $b; $lastT = $now
        if ($Total -gt 0) { Splash-Update (T 'dlp' $Text (Format-Size $b $Lang) (Format-Size $Total $Lang) ([math]::Min(100, [math]::Floor($b * 100 / $Total))) (Format-Size $speed $Lang)) }
        else { Splash-Update (T 'dlpn' $Text (Format-Size $b $Lang) (Format-Size $speed $Lang)) }
    }
    $p.WaitForExit()
    return $p.ExitCode
}
function Get-File([string]$Url, [string]$Dest, [long]$MinBytes, [string]$Label, [string]$Text = '') {
    if (-not $Text) { $Text = $Label }
    if ((Test-Path -LiteralPath $Dest) -and ((Get-Item -LiteralPath $Dest).Length -ge $MinBytes)) {
        Write-Host ("  already present: " + $Label); Splash-Step $Text; Splash-Done (T 'have' $Text); return
    }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Dest) | Out-Null
    $part = $Dest + '.part'
    Write-Host ("  downloading: " + $Label)
    Splash-Step $Text
    $total = Get-RemoteSize $Url
    for ($try = 1; $try -le 3; $try++) {
        $code = Invoke-Download $Url $part $Text $total
        if ($code -eq 33) { Remove-Item -LiteralPath $part -Force -ErrorAction SilentlyContinue; continue }   # bad resume range
        if ($code -eq 0 -and (Test-Path -LiteralPath $part) -and ((Get-Item -LiteralPath $part).Length -ge $MinBytes)) {
            Move-Item -LiteralPath $part -Destination $Dest -Force
            Splash-Done (T 'dlok' $Text (Format-Size ((Get-Item -LiteralPath $Dest).Length) $Lang)); return
        }
        Write-Host ("  attempt {0} failed (curl exit {1})" -f $try, $code) -ForegroundColor Yellow
    }
    throw ("Download failed: " + $Label + "  <-  " + $Url)
}

function Get-NvidiaInfo {
    $cands = @('nvidia-smi', (Join-Path $env:SystemRoot 'System32\nvidia-smi.exe'), 'C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe')
    foreach ($c in $cands) {
        try {
            $out = & $c --query-gpu=name,memory.total,driver_version --format=csv,noheader,nounits 2>$null
            if ($LASTEXITCODE -eq 0 -and $out) {
                $best = $null
                foreach ($line in @($out)) {
                    $p = $line.Split(',') | ForEach-Object { $_.Trim() }
                    if ($p.Count -ge 3) {
                        $o = [pscustomobject]@{ Name = $p[0]; MiB = [int]$p[1]; Driver = [double]($p[2].Split('.')[0]) }
                        if (-not $best -or $o.MiB -gt $best.MiB) { $best = $o }
                    }
                }
                if ($best) { return $best }
            }
        } catch { }
    }
    return $null
}

# ------------------------------------------------------------------ 0. checks
Step '0/7' (T 's0')
$gpu = Get-NvidiaInfo
if (-not $gpu) { throw 'No NVIDIA graphics card (or no NVIDIA driver) was found. ArtFlawless Studio needs an NVIDIA card with at least 8 GB of video memory.' }
Write-Host ("  GPU: {0}, {1} MiB, driver {2}" -f $gpu.Name, $gpu.MiB, $gpu.Driver)
Splash-Done (T 'gpu' $gpu.Name ([math]::Round($gpu.MiB / 1024)) $gpu.Driver)
if ($gpu.MiB -lt 7900) { throw ("Your graphics card has only {0} MiB video memory; at least 8 GB is required." -f $gpu.MiB) }
$weightDtype = if ($gpu.MiB -lt 14000) { 'fp8_e4m3fn' } else { 'default' }
$archive = if ($gpu.Driver -ge 580) { 'ComfyUI_windows_portable_nvidia.7z' } else { 'ComfyUI_windows_portable_nvidia_cu126.7z' }
if ($gpu.Driver -lt 580) { Write-Host '  older NVIDIA driver: using the CUDA 12.6 build of ComfyUI' }
if (-not (Test-Path -LiteralPath $Curl)) { throw 'curl.exe was not found (Windows 10 version 1803 or newer is required).' }

# ------------------------------------------------------------------ 1. ComfyUI
Step '1/7' (T 's1' $ComfyTag)
if (-not (Test-Path -LiteralPath $Py)) {
    Get-File 'https://github.com/ip7z/7zip/releases/download/26.04/7zr.exe' (Join-Path $Tools '7zr.exe') 200000 '7-Zip console (7zr.exe) - used only to unpack ComfyUI'
    $arc = Join-Path $Tools $archive
    Get-File ("https://github.com/Comfy-Org/ComfyUI/releases/download/{0}/{1}" -f $ComfyTag, $archive) $arc 1500000000 ('ComfyUI ' + $archive)
    Write-Host '  unpacking (a few minutes)...'
    Splash-Step (T 'unpack' 0)
    $prog = Join-Path $Tools '7z-progress.txt'
    $z = Start-Process -FilePath (Join-Path $Tools '7zr.exe') -ArgumentList @('x', '-y', ('"-o' + $InstallDir + '"'), ('"' + $arc + '"'), '-bsp1', '-bso0', '-bse1') `
        -WindowStyle Hidden -PassThru -RedirectStandardOutput $prog
    $null = $z.Handle
    while (-not $z.HasExited) {
        Start-Sleep -Milliseconds 700
        try {
            $fs = [IO.File]::Open($prog, 'Open', 'Read', 'ReadWrite')
            try { $len = [math]::Min(4096, $fs.Length); $fs.Seek(-$len, 'End') | Out-Null; $buf = New-Object byte[] $len; [void]$fs.Read($buf, 0, $len)
                  $m = [regex]::Matches([Text.Encoding]::ASCII.GetString($buf), '(\d{1,3})%'); if ($m.Count) { Splash-Update (T 'unpack' $m[$m.Count - 1].Groups[1].Value) } }
            finally { $fs.Dispose() }
        } catch { }
    }
    $z.WaitForExit()
    Remove-Item -LiteralPath $prog -Force -ErrorAction SilentlyContinue
    if ($z.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $Py)) { throw 'Unpacking ComfyUI failed.' }
    Splash-Done (T 'unpackOk')
    Remove-Item -LiteralPath $arc -Force -ErrorAction SilentlyContinue
} else { Write-Host '  already installed'; Splash-Step (T 'comfyHave'); Splash-Done $null }

# keep torch / numpy exactly as shipped when pip installs node requirements
$constraints = Join-Path $Tools 'constraints.txt'
try {
    & $Py -s -m pip list --format=freeze 2>$null | Where-Object { $_ -match '^(torch|torchvision|torchaudio|numpy)==' } | Set-Content -Path $constraints -Encoding ASCII
} catch { Warn ('Could not pin the torch/numpy versions: ' + $_.Exception.Message) }
if (-not (Test-Path -LiteralPath $constraints)) { Set-Content -Path $constraints -Value '' -Encoding ASCII }

# ------------------------------------------------------------------ 2. custom nodes
Step '2/7' (T 's2'); Splash-Done $null
$nodeList = @(
    @{ Id = 'rgthree-comfy';              Ver = '1.0.2608210019'; Url = 'https://cdn.comfy.org/rgthree/rgthree-comfy/1.0.2608210019/node.zip' },
    @{ Id = 'comfyui-impact-pack';        Ver = '8.28.3';  Url = 'https://cdn.comfy.org/drltdata/comfyui-impact-pack/8.28.3/node.zip' },
    @{ Id = 'comfyui-impact-subpack';     Ver = '1.3.5';   Url = 'https://cdn.comfy.org/drltdata/comfyui-impact-subpack/1.3.5/node.zip' },
    @{ Id = 'comfyui_ultimatesdupscale';  Ver = '1.7.2';   Url = 'https://cdn.comfy.org/ssit/comfyui_ultimatesdupscale/1.7.2/node.zip' },
    @{ Id = 'comfyui-florence2';          Ver = '1.1.0';   Url = 'https://cdn.comfy.org/kijai/comfyui-florence2/1.1.0/node.zip' },
    @{ Id = 'comfyui-custom-scripts';     Ver = '1.2.5';   Url = 'https://cdn.comfy.org/pythongosssss/comfyui-custom-scripts/1.2.5/node.zip' },
    @{ Id = 'comfyui_controlnet_aux';     Ver = '1.1.5';   Url = 'https://cdn.comfy.org/fannovel16/comfyui_controlnet_aux/1.1.5/node.zip' },
    @{ Id = 'comfyui-image-saver';        Ver = '1.23.0';  Url = 'https://cdn.comfy.org/alexopus/comfyui-image-saver/1.23.0/node.zip' },
    @{ Id = 'prompt-manager';             Ver = '2.7.2';   Url = 'https://cdn.comfy.org/franckyb/prompt-manager/2.7.2/node.zip' },
    @{ Id = 'comfyui-gguf';               Ver = '1.1.10';  Url = 'https://cdn.comfy.org/city96/ComfyUI-GGUF/1.1.10/node.zip' }
)
$ni = 0
foreach ($n in $nodeList) {
    $ni++
    $target = Join-Path $Nodes $n.Id
    $marker = Join-Path $target '.artflow-version'
    $nodeText = T 'node' $n.Id $ni $nodeList.Count
    if ((Test-Path -LiteralPath $marker) -and ((Get-Content -LiteralPath $marker -Raw).Trim() -eq $n.Ver)) {
        Write-Host ("  already installed: {0} {1}" -f $n.Id, $n.Ver); Splash-Step $nodeText; Splash-Done (T 'nodeHave' $n.Id $ni $nodeList.Count); continue }
    try {
        $zip = Join-Path $Tools ($n.Id + '.zip')
        $tmp = Join-Path $Tools ('x_' + $n.Id)
        Get-File $n.Url $zip 1000 ("{0} {1}" -f $n.Id, $n.Ver) $nodeText
        if (Test-Path -LiteralPath $tmp) { Remove-Item -LiteralPath $tmp -Recurse -Force }
        Expand-Archive -LiteralPath $zip -DestinationPath $tmp -Force
        $items = @(Get-ChildItem -LiteralPath $tmp -Force)
        $src = if ($items.Count -eq 1 -and $items[0].PSIsContainer) { $items[0].FullName } else { $tmp }
        if (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target -Recurse -Force }
        New-Item -ItemType Directory -Force -Path $Nodes | Out-Null
        Move-Item -LiteralPath $src -Destination $target
        Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $zip -Force -ErrorAction SilentlyContinue
        $req = Join-Path $target 'requirements.txt'
        if (Test-Path -LiteralPath $req) {
            Write-Host ("  installing Python packages for " + $n.Id)
            Splash-Step (T 'pip' $n.Id)
            # lines that need git (e.g. the optional SAM2 package of the Impact Pack) cannot be installed without git: leave them out
            $reqLines = @(Get-Content -LiteralPath $req)
            $okLines = @($reqLines | Where-Object { $_ -notmatch '^\s*git\+' -and $_ -notmatch '@\s*git\+' })
            if ($okLines.Count -lt $reqLines.Count) { Write-Host '  (skipping optional packages that need git)' -ForegroundColor Yellow }
            $req2 = Join-Path $target 'requirements.artflow.txt'   # next to the original, so relative "-r" includes still resolve
            Set-Content -LiteralPath $req2 -Value $okLines -Encoding UTF8
            & $Py -s -m pip install -r $req2 --constraint $constraints --no-warn-script-location
            if ($LASTEXITCODE -ne 0) { throw ("pip failed for " + $n.Id) }
        }
        Set-Content -LiteralPath $marker -Value $n.Ver -Encoding ASCII
        Splash-Done (T 'nodeOk' $n.Id $ni $nodeList.Count)
    } catch {
        Warn ("{0}: {1}" -f $n.Id, $_.Exception.Message)
    }
}

# ------------------------------------------------------------------ 3. Studio
Step '3/7' (T 's3')
$studioDir = Join-Path $Nodes 'artflow-studio'
New-Item -ItemType Directory -Force -Path (Join-Path $studioDir 'web') | Out-Null
Copy-Item -LiteralPath (Join-Path $Payload 'studio\__init__.py') -Destination $studioDir -Force
Copy-Item -LiteralPath (Join-Path $Payload 'studio\catalog.json') -Destination $studioDir -Force
Copy-Item -Path (Join-Path $Payload 'studio\web\*') -Destination (Join-Path $studioDir 'web') -Force
& $Py -I (Join-Path $InstallDir 'launcher\configure.py') (Join-Path $studioDir 'web\template.json') $weightDtype
$wf = Join-Path $Comfy 'user\default\workflows'
New-Item -ItemType Directory -Force -Path $wf | Out-Null
Copy-Item -LiteralPath (Join-Path $Payload 'studio\ArtFlawless-Studio-ZImageTurbo-EN.json') -Destination $wf -Force
$oldWf = Join-Path $wf 'ArtFlow-Studio-ZImageTurbo-EN.json'   # file name used by earlier versions
if (Test-Path -LiteralPath $oldWf) { Remove-Item -LiteralPath $oldWf -Force -ErrorAction SilentlyContinue }
Copy-Item -LiteralPath (Join-Path $Payload 'artflow-logo.png') -Destination (Join-Path $InstallDir 'input') -Force
$iconPng = Join-Path $Payload 'artflow-icon.png'
if (Test-Path -LiteralPath $iconPng) { Copy-Item -LiteralPath $iconPng -Destination (Join-Path $InstallDir 'input') -Force }
# the setup language is the Studio's first language (and the start window's)
try { $ud = Join-Path $Comfy 'user'; New-Item -ItemType Directory -Force -Path $ud | Out-Null
      if (-not (Test-Path -LiteralPath (Join-Path $ud 'artflow-ui-lang.txt'))) { [IO.File]::WriteAllText((Join-Path $ud 'artflow-ui-lang.txt'), $Lang) } } catch { }
Splash-Done (T 'studioOk')
Splash-Step (T 'check')
# local content check of generated images (NudeNet detector; the Falconsai classifier is downloaded with the models)
try {
    & $Py -s -m pip install --no-deps --no-warn-script-location 'nudenet==3.4.2'
    if ($LASTEXITCODE -ne 0) { throw 'pip failed for nudenet' }
    & $Py -s -c "import importlib.util as u, sys; sys.exit(0 if u.find_spec('onnxruntime') and u.find_spec('cv2') else 1)"
    if ($LASTEXITCODE -ne 0) {
        & $Py -s -m pip install --no-warn-script-location onnxruntime opencv-python-headless --constraint $constraints
        if ($LASTEXITCODE -ne 0) { throw 'pip failed for onnxruntime' }
    }
    Write-Host '  content check (NudeNet) is ready.'
    Splash-Done (T 'checkOk')
} catch { Warn ('Content check (NudeNet): ' + $_.Exception.Message + ' - adult images may not be recognised.') }

# ------------------------------------------------------------------ 4. models
Step '4/7' (T 's4'); Splash-Done $null
$HF = 'https://huggingface.co'
$modelList = @(
    @{ Req = $true;  Rel = 'diffusion_models\z_image_turbo_bf16.safetensors'; Min = 11500000000; Label = 'Z-Image Turbo (Comfy-Org, bf16, 12.3 GB)';
       Url = "$HF/Comfy-Org/z_image_turbo/resolve/main/split_files/diffusion_models/z_image_turbo_bf16.safetensors" },
    @{ Req = $true;  Rel = 'text_encoders\qwen_3_4b.safetensors'; Min = 7500000000; Label = 'Qwen3 4B text encoder (Comfy-Org, 8 GB)';
       Url = "$HF/Comfy-Org/z_image_turbo/resolve/main/split_files/text_encoders/qwen_3_4b.safetensors" },
    @{ Req = $true;  Rel = 'vae\ae.safetensors'; Min = 300000000; Label = 'Flux VAE (ae.safetensors)';
       Url = "$HF/Comfy-Org/z_image_turbo/resolve/main/split_files/vae/ae.safetensors" },
    @{ Req = $false; Rel = 'ultralytics\bbox\face_yolov8m.pt'; Min = 48000000; Label = 'Face detector (Bingsu/adetailer)';
       Url = "$HF/Bingsu/adetailer/resolve/main/face_yolov8m.pt" },
    @{ Req = $false; Rel = 'ultralytics\bbox\hand_yolov8s.pt'; Min = 21000000; Label = 'Hand detector (Bingsu/adetailer)';
       Url = "$HF/Bingsu/adetailer/resolve/main/hand_yolov8s.pt" },
    @{ Req = $false; Rel = 'ultralytics\bbox\foot_yolov8x_v2.pt'; Min = 130000000; Label = 'Foot detector (MonetEinsley/ADetailer_CM)';
       Url = "$HF/MonetEinsley/ADetailer_CM/resolve/main/foot_yolov8x_v2.pt" },
    @{ Req = $false; Rel = 'sams\sam_vit_b_01ec64.pth'; Min = 360000000; Label = 'Segment Anything vit_b (Meta)';
       Url = 'https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth';
       Alt = "$HF/datasets/Gourieff/ReActor/resolve/main/models/sams/sam_vit_b_01ec64.pth" },
    @{ Req = $false; Rel = 'nsfw\falconsai\config.json'; Min = 200; Label = 'Content check classifier - config (Falconsai)';
       Url = "$HF/Falconsai/nsfw_image_detection/resolve/main/config.json" },
    @{ Req = $false; Rel = 'nsfw\falconsai\preprocessor_config.json'; Min = 100; Label = 'Content check classifier - preprocessor (Falconsai)';
       Url = "$HF/Falconsai/nsfw_image_detection/resolve/main/preprocessor_config.json" },
    @{ Req = $false; Rel = 'nsfw\falconsai\model.safetensors'; Min = 300000000; Label = 'Content check classifier (Falconsai, 340 MB)';
       Url = "$HF/Falconsai/nsfw_image_detection/resolve/main/model.safetensors" },
    @{ Req = $false; Rel = 'upscale_models\RealESRGAN_x4plus.safetensors'; Min = 64000000; Label = 'Real-ESRGAN x4plus (wkrettek/real-esrgan-models)';
       Url = "$HF/wkrettek/real-esrgan-models/resolve/main/realesrgan_x4plus.safetensors" },
    @{ Req = $false; Rel = 'model_patches\Z-Image-Turbo-Fun-Controlnet-Union-2.1-lite-2602-8steps.safetensors'; Min = 1900000000; Label = 'Layout ControlNet (alibaba-pai, 2 GB)';
       Url = "$HF/alibaba-pai/Z-Image-Turbo-Fun-Controlnet-Union-2.1/resolve/main/Z-Image-Turbo-Fun-Controlnet-Union-2.1-lite-2602-8steps.safetensors" }
)
$missingRequired = @()
$mi = 0
foreach ($m in $modelList) {
    $mi++
    $dest = Join-Path $Models $m.Rel
    $mText = T 'model' $m.Label $mi $modelList.Count
    try {
        try { Get-File $m.Url $dest $m.Min $m.Label $mText }
        catch { if ($m.Alt) { Write-Host '  primary source failed, trying the mirror...' -ForegroundColor Yellow; Splash-Update ($mText + ' – ' + (T 'mirror')); Get-File $m.Alt $dest $m.Min $m.Label $mText } else { throw } }
    } catch {
        if ($m.Req) { $missingRequired += $m.Rel }
        Warn ("{0}: {1}" -f $m.Label, $_.Exception.Message)
    }
}

# ------------------------------------------------------------------ 5. base LoRA
Step '5/7' (T 's5'); Splash-Done $null
$loraName = 'Hands + Feet + skin perfection style zib v1.safetensors'
$loraDest = Join-Path $Models ('loras\' + $loraName)
$loraUrl = 'https://civitai.red/api/download/models/2577477?fileId=2464717'
if ($env:CIVITAI_TOKEN) { $loraUrl += '&token=' + $env:CIVITAI_TOKEN }
try { Get-File $loraUrl $loraDest 1000000 'Hands + Feet + skin perfection style LoRA' (T 'lora') }
catch {
    Remove-Item -LiteralPath ($loraDest + '.part') -Force -ErrorAction SilentlyContinue
    $loraDir = Split-Path -Parent $loraDest
    New-Item -ItemType Directory -Force -Path $loraDir | Out-Null
    Write-Host ''
    Write-Host 'The base LoRA needs a (free) Civitai login, so it cannot be downloaded automatically.' -ForegroundColor Yellow
    Write-Host '  1. Your browser opens the download page - log in to Civitai and download the file.'
    Write-Host '  2. Save the file into this folder (a folder window opens for you):'
    Write-Host ("       " + $loraDir) -ForegroundColor Cyan
    Write-Host '     If the browser saved it to Downloads, just drag or move it into that folder.'
    Write-Host '  3. Come back here and press Enter.'
    Write-Host '  (Press Enter right away to skip this; the Studio works without the LoRA.)'
    $manualUrl = 'https://civitai.red/api/download/models/2577477?fileId=2464717'
    try { Start-Process explorer.exe -ArgumentList ('"' + $loraDir + '"') } catch { }
    try { Start-Process $manualUrl } catch { }
    $skip = -not (Splash-Ask (T 'loraAsk' $loraDir) 'ArtFlawless Studio' -OkCancel)
    # accept the file under any name in the LoRA folder or in the install folder, and give it the expected name
    $found = $null
    foreach ($dir in @($loraDir, $InstallDir)) {
        $found = Get-ChildItem -LiteralPath $dir -Filter '*.safetensors' -File -ErrorAction SilentlyContinue |
            Where-Object { $_.Length -gt 1000000 -and ($_.Name -like '*Hands*Feet*' -or $_.Name -like '*skin*perfection*') } |
            Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($found) { break }
    }
    if ($found -and -not $skip) {
        if ($found.FullName -ne $loraDest) { Move-Item -LiteralPath $found.FullName -Destination $loraDest -Force }
        Write-Host ("  LoRA is in place: " + $loraDest) -ForegroundColor Green
        Splash-Done (T 'loraOk')
    } else {
        Splash-Done (T 'loraSkip')
        Warn ("The base LoRA was skipped. To add it later, save the file as  " + $loraDest)
    }
}

# ------------------------------------------------------------------ 6. output
Step '6/7' (T 's6'); Splash-Done $null
Splash-Step (T 'host')
try {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $InstallDir 'launcher\Build-Host.ps1')
    if ($LASTEXITCODE -ne 0) { throw ('exit code ' + $LASTEXITCODE) }
    Write-Host '  Studio window (WebView2) is ready.'
    Splash-Done (T 'hostOk')
} catch { Warn ('The frameless Studio window could not be prepared (' + $_.Exception.Message + '); the Studio will open in Microsoft Edge instead.') }
Write-Host ("  input folder : " + (Join-Path $InstallDir 'input'))
Write-Host ("  output folder: " + (Join-Path $InstallDir 'output'))
Write-Host '  (the depth-map model and Florence-2 are downloaded automatically the first time they are used)'

Write-Host ''; Write-Host '[7/7] Summary' -ForegroundColor Cyan
if ($Warnings.Count) {
    Write-Host ("{0} warning(s):" -f $Warnings.Count) -ForegroundColor Yellow
    $Warnings | ForEach-Object { Write-Host ("  - " + $_) -ForegroundColor Yellow }
    Write-Host '  ArtFlawless Studio lists anything that is missing when it starts, and the installer can be re-run to retry.'
} else { Write-Host 'Everything was installed.' -ForegroundColor Green }
try { Stop-Transcript | Out-Null } catch { }

if ($missingRequired.Count -or -not (Test-Path -LiteralPath $Py)) {
    Write-Host ''
    Write-Host ('The base model files are missing: ' + ($missingRequired -join ', ')) -ForegroundColor Red
    Splash-Error (T 'stop' ($missingRequired -join ', '))
    [void](Splash-Ask (T 'sumMiss' ($missingRequired -join "`n")))
    Close-ArtSplash
    exit 2
}
if ($Warnings.Count) {
    Splash-Step (T 'warnN' $Warnings.Count); Splash-Done $null
    [void](Splash-Ask (T 'sumWarn' $Warnings.Count (($Warnings | ForEach-Object { '- ' + $_ }) -join "`n")))
} else {
    Splash-Step (T 'allOk'); Splash-Done $null; Start-Sleep -Milliseconds 1200
}
Close-ArtSplash
exit 0
