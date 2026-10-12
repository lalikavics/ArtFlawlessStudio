; SPDX-License-Identifier: GPL-3.0-or-later
; Copyright (C) 2026 Lalikavics - ArtFlawless Studio
; ArtFlawless Studio installer - Inno Setup 6
; Build: open this file in Inno Setup (or run build.bat). Output: Output\ArtFlawlessStudio-Setup-<VERSION>.exe

#define AppName "ArtFlawless Studio"
; the version comes from the VERSION file (single source for the setup and the Studio)
#define VerFile FileOpen(AddBackslash(SourcePath) + "VERSION")
#define AppVersion Trim(FileRead(VerFile))
#expr FileClose(VerFile)
#undef VerFile
#define UrlFile FileOpen(AddBackslash(SourcePath) + "REPO_URL")
#define RepoUrl Trim(FileRead(UrlFile))
#expr FileClose(UrlFile)
#undef UrlFile
#ifndef MinFree
  #define MinFree 45
#endif

[Setup]
AppId={{4F94F30E-317E-449D-AEF3-74743F947270}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Lalikavics
AppContact={#RepoUrl}/issues
AppPublisherURL={#RepoUrl}
AppSupportURL={#RepoUrl}/issues
AppUpdatesURL={#RepoUrl}/releases
DefaultDirName={code:DefDir}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
MinVersion=10.0.17134
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=assets\artflow.ico
UninstallDisplayIcon={app}\launcher\artflow.ico
InfoBeforeFile=studio_out\info.txt
OutputDir=Output
OutputBaseFilename=ArtFlawlessStudio-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UsePreviousAppDir=no

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "hu"; MessagesFile: "compiler:Languages\Hungarian.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; Flags: checkedonce

[Dirs]
Name: "{app}\input"
Name: "{app}\output"

[Files]
Source: "launcher\ArtFlow-Launcher.ps1";        DestDir: "{app}\launcher"
Source: "launcher\Install-Components.ps1";      DestDir: "{app}\launcher"
Source: "launcher\Build-Host.ps1";              DestDir: "{app}\launcher"
Source: "launcher\ArtFlawlessHost.cs";          DestDir: "{app}\launcher"
Source: "launcher\configure.py";                DestDir: "{app}\launcher"
Source: "assets\artflow.ico";                   DestDir: "{app}\launcher"
Source: "assets\artflow-logo.png";              DestDir: "{app}\launcher\payload"
Source: "studio_out\__init__.py";               DestDir: "{app}\launcher\payload\studio"
Source: "studio_out\catalog.json";              DestDir: "{app}\launcher\payload\studio"
Source: "studio_out\ArtFlow-Studio-ZImageTurbo-EN.json"; DestDir: "{app}\launcher\payload\studio"
Source: "studio_out\web\*";                     DestDir: "{app}\launcher\payload\studio\web"; Flags: recursesubdirs

[Icons]
Name: "{autodesktop}\ArtFlawless Studio"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ""{app}\launcher\ArtFlow-Launcher.ps1"""; \
  WorkingDir: "{app}"; IconFilename: "{app}\launcher\artflow.ico"; Tasks: desktopicon
Name: "{autoprograms}\ArtFlawless Studio"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ""{app}\launcher\ArtFlow-Launcher.ps1"""; \
  WorkingDir: "{app}"; IconFilename: "{app}\launcher\artflow.ico"

[Run]
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ""{app}\launcher\ArtFlow-Launcher.ps1"""; \
  Description: "Start ArtFlawless Studio"; Flags: nowait postinstall skipifsilent runhidden

[InstallDelete]
; shortcuts of the old name (ArtFlow Studio, up to 1.1.0)
Type: files; Name: "{autodesktop}\ArtFlow Studio.lnk"
Type: files; Name: "{autoprograms}\ArtFlow Studio.lnk"

[UninstallDelete]
; the input and output folders (your images) are kept
Type: filesandordirs; Name: "{app}\ComfyUI_windows_portable"
Type: filesandordirs; Name: "{app}\launcher"
Type: filesandordirs; Name: "{app}\edge-profile"
Type: filesandordirs; Name: "{app}\studio-window"

[Code]
const
  MinFreeGB = {#MinFree};
  MinVramMiB = 7900;

var
  GpuName: String;
  GpuMiB: Integer;

{ run nvidia-smi through cmd and read the biggest GPU; returns False if it could not be read }
function ReadGpu(const Exe: String): Boolean;
var
  Tmp: String;
  Lines: TArrayOfString;
  ResultCode, I, J, V: Integer;
  Line: String;
begin
  Result := False;
  Tmp := ExpandConstant('{tmp}\gpu.txt');
  DeleteFile(Tmp);
  if not Exec(ExpandConstant('{cmd}'),
    '/C ""' + Exe + '" --query-gpu=name,memory.total --format=csv,noheader,nounits > "' + Tmp + '" 2>nul"',
    '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then Exit;
  if not LoadStringsFromFile(Tmp, Lines) then Exit;
  for I := 0 to GetArrayLength(Lines) - 1 do
  begin
    Line := Trim(Lines[I]);
    J := Length(Line);
    while (J > 0) and (Line[J] <> ',') do J := J - 1;
    if J > 1 then
    begin
      V := StrToIntDef(Trim(Copy(Line, J + 1, Length(Line))), 0);
      if V > GpuMiB then
      begin
        GpuMiB := V;
        GpuName := Trim(Copy(Line, 1, J - 1));
        Result := True;
      end;
    end;
  end;
end;

const
  UninstKey = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{4F94F30E-317E-449D-AEF3-74743F947270}_is1';

{ folder of an earlier installation (ArtFlow Studio 1.0/1.1 or ArtFlawless Studio), '' if none }
function PrevDir(): String;
var
  S: String;
begin
  S := '';
  if not RegQueryStringValue(HKCU, UninstKey, 'Inno Setup: App Path', S) then
    if not RegQueryStringValue(HKLM, UninstKey, 'Inno Setup: App Path', S) then
      S := '';
  if (S = '') and DirExists(ExpandConstant('{sd}\ArtFlowStudio')) then
    S := ExpandConstant('{sd}\ArtFlowStudio');
  if (S <> '') and not DirExists(S) then
    S := '';
  Result := RemoveBackslashUnlessRoot(S);
end;

{ default folder: the old "ArtFlowStudio" folder gets the new name, any other earlier folder is kept }
function DefDir(Param: String): String;
var
  Old: String;
begin
  Old := PrevDir();
  if Old = '' then
    Result := ExpandConstant('{sd}\ArtFlawlessStudio')
  else if CompareText(ExtractFileName(Old), 'ArtFlowStudio') = 0 then
    Result := ExtractFilePath(Old) + 'ArtFlawlessStudio'
  else
    Result := Old;
end;

{ moves (renames) the earlier installation into the chosen folder, so nothing has to be downloaded again }
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Old, New: String;
begin
  Result := '';
  Old := PrevDir();
  New := RemoveBackslashUnlessRoot(ExpandConstant('{app}'));
  if (Old <> '') and (CompareText(Old, New) <> 0) and (not DirExists(New)) and (CompareText(ExtractFileDrive(Old), ExtractFileDrive(New)) = 0) then
  begin
    if not RenameFile(Old, New) then
      Result := 'The earlier installation folder (' + Old + ') could not be moved to ' + New + '.' + #13#10 + #13#10 +
        'Please close ArtFlawless Studio (and any Explorer window or program that uses that folder) and run the setup again.';
  end;
end;

function HasEdge(): Boolean;
begin
  Result := FileExists(ExpandConstant('{commonpf32}') + '\Microsoft\Edge\Application\msedge.exe') or
            FileExists(ExpandConstant('{commonpf64}') + '\Microsoft\Edge\Application\msedge.exe') or
            FileExists(ExpandConstant('{localappdata}') + '\Microsoft\Edge\Application\msedge.exe') or
            RegKeyExists(HKLM, 'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe');
end;

function HasWebView2(): Boolean;
var
  V: String;
begin
  Result := (RegQueryStringValue(HKLM, 'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', V) and (V <> '') and (V <> '0.0.0.0')) or
            (RegQueryStringValue(HKCU, 'Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', V) and (V <> '') and (V <> '0.0.0.0'));
end;

function InitializeSetup(): Boolean;
var
  Code: Integer;
begin
  Result := True;
  GpuMiB := 0;
  GpuName := '';
  if not ReadGpu('nvidia-smi') then
    ReadGpu(ExpandConstant('{commonpf64}') + '\NVIDIA Corporation\NVSMI\nvidia-smi.exe');
  if GpuMiB = 0 then
  begin
    MsgBox('No NVIDIA graphics card (or NVIDIA driver) was found.' + #13#10 + #13#10 +
      'ArtFlawless Studio needs an NVIDIA card with at least 8 GB of video memory and an up-to-date NVIDIA driver.',
      mbCriticalError, MB_OK);
    Result := False;
  end
  else if GpuMiB < MinVramMiB then
  begin
    MsgBox('Your graphics card (' + GpuName + ') has only ' + IntToStr(GpuMiB) + ' MiB of video memory.' + #13#10 +
      'At least 8 GB is required.', mbCriticalError, MB_OK);
    Result := False;
  end;
  if Result and not HasEdge() then
  begin
    if MsgBox('Microsoft Edge was not found on this computer.' + #13#10 + #13#10 +
      'ArtFlawless Studio needs Microsoft Edge (it is part of Windows 10 and 11 and provides the engine of the Studio window).' + #13#10 +
      'Do you want to open the Edge download page now? Run this setup again after installing it.', mbError, MB_YESNO) = IDYES then
      ShellExec('open', 'https://www.microsoft.com/edge', '', '', SW_SHOWNORMAL, ewNoWait, Code);
    Result := False;
  end
  else if Result and not HasWebView2() then
    MsgBox('The Microsoft Edge WebView2 Runtime was not found.' + #13#10 + #13#10 +
      'The Studio will open in a normal Microsoft Edge window. For the frameless Studio window, install the "Evergreen" WebView2 Runtime from' + #13#10 +
      'https://developer.microsoft.com/microsoft-edge/webview2/', mbInformation, MB_OK);
end;

function HasNonAscii(const S: String): Boolean;
var
  I: Integer;
begin
  Result := False;
  for I := 1 to Length(S) do
    if Ord(S[I]) > 127 then Result := True;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  FreeMB, TotalMB: Cardinal;
  Drive: String;
begin
  Result := True;
  if CurPageID = wpSelectDir then
  begin
    if HasNonAscii(WizardDirValue) then
    begin
      MsgBox('Please choose a folder whose path has no accented or special characters (for example C:\ArtFlawlessStudio). ' +
        'The AI components do not work reliably from such paths.', mbError, MB_OK);
      Result := False;
      Exit;
    end;
    Drive := ExtractFileDrive(WizardDirValue) + '\';
    if GetSpaceOnDisk(Drive, True, FreeMB, TotalMB) then
      if FreeMB < (MinFreeGB * 1024) then
      begin
        MsgBox('About ' + IntToStr(MinFreeGB) + ' GB of free space is needed on ' + Drive +
          ' (models and tools are downloaded during setup), but only ' + IntToStr(FreeMB div 1024) +
          ' GB is free. Please choose another folder or drive.', mbError, MB_OK);
        Result := False;
      end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  Ps, Args: String;
begin
  if CurStep = ssPostInstall then
  begin
    WizardForm.StatusLabel.Caption := 'Downloading the AI components - see the console window (this takes a long time)...';
    Ps := ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe');
    Args := '-NoProfile -ExecutionPolicy Bypass -File "' + ExpandConstant('{app}\launcher\Install-Components.ps1') +
      '" -InstallDir "' + ExpandConstant('{app}') + '"';
    if not Exec(Ps, Args, '', SW_SHOW, ewWaitUntilTerminated, ResultCode) then
      MsgBox('The component installer could not be started.', mbError, MB_OK)
    else if ResultCode <> 0 then
      MsgBox('The component download did not finish (code ' + IntToStr(ResultCode) + ').' + #13#10 +
        'Run this setup again to resume where it stopped.' + #13#10 +
        'Log: ' + ExpandConstant('{app}\launcher\install.log'), mbError, MB_OK);
  end;
end;
