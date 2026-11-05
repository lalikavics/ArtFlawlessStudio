# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Lalikavics - ArtFlawless Studio
# Start / setup window for the launcher and the component installer (dot-sourced by both).
# ArtSplash.cs is compiled once into launcher\splash\ArtSplash.dll (again only when the source is newer); when that is not
# possible the functions below do nothing and questions fall back to a plain message box.
$script:SplashOk = $false
$script:SplashDir = $PSScriptRoot

# the language the Studio was last used in (written by the Studio); English until then
function Get-UiLang([string]$ComfyDir, [string]$Default = 'en') {
    try {
        $f = Join-Path $ComfyDir 'user\artflow-ui-lang.txt'
        if (Test-Path -LiteralPath $f) { $l = ([IO.File]::ReadAllText($f)).Trim().ToLowerInvariant(); if ($l -in @('hu', 'en')) { return $l } }
    } catch { }
    return $Default
}

function Start-ArtSplash([bool]$OnTop = $true) {
    try {
        Add-Type -AssemblyName System.Windows.Forms, System.Drawing
        if (-not ('ArtSplash' -as [type])) {
            $src = Join-Path $script:SplashDir 'ArtSplash.cs'
            $dll = Join-Path $script:SplashDir 'splash\ArtSplash.dll'
            $stale = (-not (Test-Path -LiteralPath $dll)) -or ((Get-Item -LiteralPath $src).LastWriteTimeUtc -gt (Get-Item -LiteralPath $dll).LastWriteTimeUtc)
            $loaded = $false
            if ($stale) {
                try {
                    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dll) | Out-Null
                    if (Test-Path -LiteralPath $dll) { Remove-Item -LiteralPath $dll -Force }
                    Add-Type -TypeDefinition ([IO.File]::ReadAllText($src)) -ReferencedAssemblies System.Windows.Forms, System.Drawing -OutputAssembly $dll -OutputType Library -ErrorAction Stop
                } catch { }
            }
            if (Test-Path -LiteralPath $dll) { try { Add-Type -Path $dll -ErrorAction Stop; $loaded = $true } catch { } }
            if (-not $loaded -and -not ('ArtSplash' -as [type])) {
                Add-Type -TypeDefinition ([IO.File]::ReadAllText($src)) -ReferencedAssemblies System.Windows.Forms, System.Drawing -ErrorAction Stop
            }
        }
        [ArtSplash]::Start((Join-Path $script:SplashDir 'splash-bg.png'), (Join-Path $script:SplashDir 'artflow.ico'), $OnTop)
        $script:SplashOk = $true
    } catch { $script:SplashOk = $false }
    return $script:SplashOk
}
function Splash-Step([string]$t)   { if ($script:SplashOk) { [ArtSplash]::Step($t) } }
function Splash-Update([string]$t) { if ($script:SplashOk) { [ArtSplash]::Update($t) } }
function Splash-Done([string]$t)   { if ($script:SplashOk) { [ArtSplash]::Done($t) } }
function Splash-Note([string]$t)   { if ($script:SplashOk) { [ArtSplash]::Note($t) } }
function Splash-Error([string]$t)  { if ($script:SplashOk) { [ArtSplash]::Error($t) } }
function Splash-Fail([string]$t)   { if ($script:SplashOk) { [ArtSplash]::Fail($t) } }
# when the window cannot be shown, the hidden console of the installer is shown instead
function Show-Console {
    try {
        if (-not ('AfCon' -as [type])) { Add-Type -ErrorAction Stop 'using System; using System.Runtime.InteropServices; public static class AfCon { [DllImport("kernel32.dll")] public static extern IntPtr GetConsoleWindow(); [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c); }' }
        [void][AfCon]::ShowWindow([AfCon]::GetConsoleWindow(), 5)
    } catch { }
}
function Close-ArtSplash           { if ($script:SplashOk) { try { [ArtSplash]::Close() } catch { }; $script:SplashOk = $false } }
# a message over the window; with -OkCancel returns $true for OK
function Splash-Ask([string]$Text, [string]$Caption = 'ArtFlawless Studio', [switch]$OkCancel) {
    if ($script:SplashOk) { return [ArtSplash]::Ask($Text, $Caption, [bool]$OkCancel) }
    $r = [System.Windows.Forms.MessageBox]::Show($Text, $Caption, $(if ($OkCancel) { 'OKCancel' } else { 'OK' }))
    return ($r -eq 'OK')
}

# "3.2 / 12.3 GB" style sizes
function Format-Size([double]$b, [string]$lang = 'en') {
    $u = 'B'; $v = $b
    foreach ($x in @('KB', 'MB', 'GB')) { if ($v -ge 1024) { $v /= 1024; $u = $x } }
    $inv = [Globalization.CultureInfo]::InvariantCulture
    $s = if ($u -eq 'GB') { $v.ToString('0.0', $inv) } else { $v.ToString('0', $inv) }
    if ($lang -eq 'hu') { $s = $s.Replace('.', ',') }
    return "$s $u"
}
