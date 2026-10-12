# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Lalikavics - ArtFlawless Studio
# Builds the frameless Studio window (ArtFlawlessHost.exe) on this computer:
# downloads the WebView2 SDK files from nuget.org once, then compiles ArtFlawlessHost.cs with the
# C# compiler that ships with Windows (.NET Framework). Safe to run again; it only rebuilds when needed.
$ErrorActionPreference = 'Stop'
$Here = $PSScriptRoot
$Dir = Join-Path $Here 'webview2'
$Exe = Join-Path $Dir 'ArtFlawlessHost.exe'
$Src = Join-Path $Here 'ArtFlawlessHost.cs'
$Ver = '1.0.3912.50'
New-Item -ItemType Directory -Force -Path $Dir | Out-Null

$need = @('Microsoft.Web.WebView2.Core.dll', 'Microsoft.Web.WebView2.WinForms.dll', 'WebView2Loader.dll')
if (@($need | Where-Object { -not (Test-Path -LiteralPath (Join-Path $Dir $_)) }).Count) {
    $pkg = Join-Path $env:TEMP ("webview2-sdk-" + $Ver + ".zip")
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    $old = $ProgressPreference; $ProgressPreference = 'SilentlyContinue'
    try { Invoke-WebRequest -UseBasicParsing -Uri ("https://www.nuget.org/api/v2/package/Microsoft.Web.WebView2/" + $Ver) -OutFile $pkg }
    finally { $ProgressPreference = $old }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [IO.Compression.ZipFile]::OpenRead($pkg)
    try {
        foreach ($e in $zip.Entries) {
            $n = $e.FullName.Replace('\', '/').ToLowerInvariant()
            $take = (($n -like 'lib/net462/*') -and ($e.Name -eq 'Microsoft.Web.WebView2.Core.dll' -or $e.Name -eq 'Microsoft.Web.WebView2.WinForms.dll')) -or
                    (($n -like 'runtimes/win-x64/native/*') -and $e.Name -eq 'WebView2Loader.dll')
            if ($take) { [IO.Compression.ZipFileExtensions]::ExtractToFile($e, (Join-Path $Dir $e.Name), $true) }
        }
    } finally { $zip.Dispose() }
    Remove-Item -LiteralPath $pkg -Force -ErrorAction SilentlyContinue
    foreach ($f in $need) { if (-not (Test-Path -LiteralPath (Join-Path $Dir $f))) { throw "WebView2 SDK file missing after download: $f" } }
}

if (-not (Test-Path -LiteralPath $Exe) -or (Get-Item -LiteralPath $Src).LastWriteTimeUtc -gt (Get-Item -LiteralPath $Exe).LastWriteTimeUtc) {
    if (Test-Path -LiteralPath $Exe) { Remove-Item -LiteralPath $Exe -Force }
    $refs = @('System.dll', 'System.Drawing.dll', 'System.Windows.Forms.dll',
        (Join-Path $Dir 'Microsoft.Web.WebView2.Core.dll'), (Join-Path $Dir 'Microsoft.Web.WebView2.WinForms.dll'))
    Add-Type -TypeDefinition ([IO.File]::ReadAllText($Src)) -ReferencedAssemblies $refs -OutputAssembly $Exe -OutputType WindowsApplication -IgnoreWarnings
}
if (-not (Test-Path -LiteralPath $Exe)) { throw 'ArtFlawlessHost.exe was not built.' }
