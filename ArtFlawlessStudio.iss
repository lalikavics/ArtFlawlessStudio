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
Source: "studio_out\ArtFlawless-Studio-ZImageTurbo-EN.json"; DestDir: "{app}\launcher\payload\studio"
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

{ folder of an earlier installation, '' if none }
function PrevDir(): String;
var
  S: String;
begin
  S := '';
  if not RegQueryStringValue(HKCU, UninstKey, 'Inno Setup: App Path', S) then
    if not RegQueryStringValue(HKLM, UninstKey, 'Inno Setup: App Path', S) then
      S := '';
  if (S <> '') and not DirExists(S) then
    S := '';
  Result := RemoveBackslashUnlessRoot(S);
end;

var
  IsUpdate: Boolean;
  OldVer, OldDir: String;

function IsHu(): Boolean;
begin
  Result := ActiveLanguage = 'hu';
end;

{ version of the earlier installation from the uninstall entry, '' if unknown (1.0 had none) }
function PrevVersion(): String;
var
  S: String;
begin
  S := '';
  if not RegQueryStringValue(HKCU, UninstKey, 'DisplayVersion', S) then
    if not RegQueryStringValue(HKLM, UninstKey, 'DisplayVersion', S) then
      S := '';
  Result := Trim(S);
end;

{ next number of a dotted version string, removed from S }
function TakeNum(var S: String): Integer;
var
  P: Integer;
begin
  P := Pos('.', S);
  if P = 0 then begin Result := StrToIntDef(S, 0); S := ''; end
  else begin Result := StrToIntDef(Copy(S, 1, P - 1), 0); Delete(S, 1, P); end;
end;

{ -1 if A < B, 0 if equal, 1 if A > B (MAJOR.MINOR.PATCH) }
function VerCmp(A, B: String): Integer;
var
  I, X, Y: Integer;
begin
  Result := 0;
  for I := 1 to 3 do
  begin
    X := TakeNum(A); Y := TakeNum(B);
    if X < Y then begin Result := -1; Exit; end;
    if X > Y then begin Result := 1; Exit; end;
  end;
end;

{ True while the Studio (ComfyUI on port 8199) is running }
function StudioRunning(): Boolean;
var
  Code: Integer;
begin
  Result := Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'),
    '-NoProfile -Command "if (Get-NetTCPConnection -LocalPort 8199 -State Listen -ErrorAction SilentlyContinue) { exit 5 } else { exit 0 }"',
    '', SW_HIDE, ewWaitUntilTerminated, Code) and (Code = 5);
end;

{ default folder: the folder of an earlier installation, otherwise C:\ArtFlawlessStudio }
function DefDir(Param: String): String;
begin
  Result := PrevDir();
  if Result = '' then
    Result := ExpandConstant('{sd}\ArtFlawlessStudio');
end;

{ the Studio has to be closed before its files are replaced }
function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  while StudioRunning() do
  begin
    if IsHu() then
    begin
      if MsgBox('Az ArtFlawless Studio most fut.' + #13#10 + #13#10 + 'Zárd be a Studio ablakát (és várd meg, amíg a háttérben futó ComfyUI is leáll), majd kattints az OK gombra.',
        mbInformation, MB_OKCANCEL) = IDCANCEL then begin Result := 'Az ArtFlawless Studio még fut. Zárd be, és indítsd újra a telepítőt.'; Exit; end;
    end
    else if MsgBox('ArtFlawless Studio is running.' + #13#10 + #13#10 + 'Please close the Studio window (and wait until ComfyUI in the background has stopped), then click OK.',
      mbInformation, MB_OKCANCEL) = IDCANCEL then begin Result := 'ArtFlawless Studio is still running. Close it and run the setup again.'; Exit; end;
    Sleep(1500);
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
  Msg, Keep, Q: String;
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
  if not Result then Exit;
  OldDir := PrevDir();
  IsUpdate := OldDir <> '';
  if not IsUpdate then Exit;
  OldVer := PrevVersion();
  if OldVer = '' then
    Msg := 'an earlier version'
  else
    Msg := 'version ' + OldVer;
  if IsHu() then
  begin
    if OldVer = '' then Msg := 'egy korábbi verziója' else Msg := 'a(z) ' + OldVer + ' verziója';
    Keep := 'A képeid (input és output mappa), a mentett munkafolyamatok, a letöltött modellek és a beállítások megmaradnak; csak a program fájljai cserélődnek ki.';
    if (OldVer <> '') and (VerCmp(OldVer, '{#AppVersion}') = 0) then
      Q := 'Az ArtFlawless Studio {#AppVersion} már telepítve van ide:' + #13#10 + OldDir + #13#10 + #13#10 + 'Újratelepíted (javítás)?' + #13#10 + #13#10 + Keep
    else if (OldVer <> '') and (VerCmp(OldVer, '{#AppVersion}') > 0) then
      Q := 'Az ArtFlawless Studio újabb verziója (' + OldVer + ') van telepítve ide:' + #13#10 + OldDir + #13#10 + #13#10 +
        'Ez a telepítő régebbi ({#AppVersion}). Biztosan visszaállsz erre a verzióra?' + #13#10 + #13#10 + Keep
    else
      Q := 'Az ArtFlawless Studio ' + Msg + ' van telepítve ide:' + #13#10 + OldDir + #13#10 + #13#10 + 'Frissíted a(z) {#AppVersion} verzióra?' + #13#10 + #13#10 + Keep;
  end
  else
  begin
    Keep := 'Your images (input and output folders), saved workflows, downloaded models and settings are kept; only the program files are replaced.';
    if (OldVer <> '') and (VerCmp(OldVer, '{#AppVersion}') = 0) then
      Q := 'ArtFlawless Studio {#AppVersion} is already installed in:' + #13#10 + OldDir + #13#10 + #13#10 + 'Do you want to reinstall (repair) it?' + #13#10 + #13#10 + Keep
    else if (OldVer <> '') and (VerCmp(OldVer, '{#AppVersion}') > 0) then
      Q := 'A newer version of ArtFlawless Studio (' + OldVer + ') is installed in:' + #13#10 + OldDir + #13#10 + #13#10 +
        'This setup is older ({#AppVersion}). Do you really want to go back to this version?' + #13#10 + #13#10 + Keep
    else
      Q := 'ArtFlawless Studio (' + Msg + ') is installed in:' + #13#10 + OldDir + #13#10 + #13#10 + 'Do you want to update it to version {#AppVersion}?' + #13#10 + #13#10 + Keep;
  end;
  if (OldVer <> '') and (VerCmp(OldVer, '{#AppVersion}') > 0) then
    Result := MsgBox(Q, mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES
  else
    Result := MsgBox(Q, mbConfirmation, MB_YESNO) = IDYES;
end;

{ an update goes into the same folder: no folder, info or task pages }
function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := IsUpdate and ((PageID = wpSelectDir) or (PageID = wpInfoBefore) or (PageID = wpSelectTasks));
end;

function HasNonAscii(const S: String): Boolean;
var
  I: Integer;
begin
  Result := False;
  for I := 1 to Length(S) do
    if Ord(S[I]) > 127 then Result := True;
end;

var
  AgePage: TWizardPage;
  AgeMemo: TNewMemo;
  AgeCheck: TNewCheckBox;

procedure AgeCheckClick(Sender: TObject);
begin
  WizardForm.NextButton.Enabled := AgeCheck.Checked;
end;

{ the 18+ declaration: shown on every install and update, the Next button ("I accept") works only when the box is ticked }
procedure InitializeWizard();
begin
  if IsHu() then
    AgePage := CreateCustomPage(wpWelcome, 'Korhatár és felelős használat', 'Kérlek, olvasd el, és erősítsd meg a folytatáshoz.')
  else
    AgePage := CreateCustomPage(wpWelcome, 'Age requirement and responsible use', 'Please read this and confirm it to continue.');
  AgeMemo := TNewMemo.Create(AgePage);
  AgeMemo.Parent := AgePage.Surface;
  AgeMemo.Left := 0; AgeMemo.Top := 0;
  AgeMemo.Width := AgePage.SurfaceWidth;
  AgeMemo.Height := AgePage.SurfaceHeight - ScaleY(34);
  AgeMemo.ReadOnly := True;
  AgeMemo.ScrollBars := ssVertical;
  AgeMemo.WordWrap := True;
  if IsHu() then
    AgeMemo.Text := 'Az ArtFlawless Studiót csak felnőtt (18. életévét betöltött) személy használhatja.' + #13#10 +
    '' + #13#10 +
    'A programba épített védelem:' + #13#10 +
    '- Tartalomszűrő: a felnőtt tartalmúnak (meztelenség, szexuális tartalom) felismert képek homályosítva jelennek meg, és az output\18+ mappába kerülnek. Alapból be van kapcsolva; a beállításokban kikapcsolható, miután megerősítetted, hogy elmúltál 18 éves.' + #13#10 +
    '- Biztonságos mód: a modelleket a meztelenség elkerülésére ösztönzi. Alapból be van kapcsolva, kikapcsolható.' + #13#10 +
    '- Gyermekvédelem: ha a prompt kiskorúra utal meztelenséggel vagy szexuális tartalommal együtt, a program mindig megtagadja a generálást. Ez nem kapcsolható ki. Kiskorúak szexuális ábrázolása tilos, a mesterséges és MI-vel készített is (2011/93/EU irányelv: https://eur-lex.europa.eu/eli/dir/2011/93/oj).' + #13#10 +
    '- MI-jelölés: a generált PNG-képek géppel olvasható „MI által készített” jelölést kapnak, az EU MI-rendelet 50. cikkének szellemében ((EU) 2024/1689 rendelet: https://eur-lex.europa.eu/eli/reg/2024/1689/oj).' + #13#10 +
    '' + #13#10 +
    'A felismerés automatikus, és nem tökéletes: tévedhet mindkét irányba.' + #13#10 +
    '' + #13#10 +
    'Az AI-modelleket nem az ArtFlawless Studio szerzője készítette, és nem ő terjeszti: a telepítő az eredeti forrásukból tölti le őket, és mindegyikre a saját licence vonatkozik. Az ArtFlawless Studio igyekszik csökkenteni a visszaélés kockázatát, de nyílt forráskódú szoftverként ezt teljesen kizárni nem tudja. Aki ezeket a védelmeket megkerüli, vagy a programot ennek érdekében átírja, a saját felelősségére teszi; ehhez a szerző nem járul hozzá, és ezért nem vállal felelősséget.' + #13#10 +
    '' + #13#10 +
    'Kizárólag te felelsz azért, amit létrehozol, és azért, ahogyan felhasználod, beleértve a rád vonatkozó jogszabályokat és mások jogait is. Valós személyt ne ábrázolj a beleegyezése nélkül.'
  else
    AgeMemo.Text := 'ArtFlawless Studio may only be used by adults (18 years or older).' + #13#10 +
    '' + #13#10 +
    'Protection built into the program:' + #13#10 +
    '- Content filter: images recognised as adult content (nudity, sexual content) are blurred and saved into the output\18+ folder. It is on by default and can be switched off in the Settings after confirming that you are 18 or older.' + #13#10 +
    '- Safe mode: steers the models away from nudity. On by default, can be switched off.' + #13#10 +
    '- Child protection: a prompt that refers to a minor together with nudity or sexual content is always refused. This cannot be switched off. Sexual depictions of minors are illegal, including artificial and AI-generated ones (EU Directive 2011/93/EU: https://eur-lex.europa.eu/eli/dir/2011/93/oj).' + #13#10 +
    '- AI marking: generated PNG images carry a machine-readable "AI-generated" mark, in the spirit of Article 50 of the EU AI Act (Regulation (EU) 2024/1689: https://eur-lex.europa.eu/eli/reg/2024/1689/oj).' + #13#10 +
    '' + #13#10 +
    'The recognition is automatic and not perfect: it can miss content or flag harmless images.' + #13#10 +
    '' + #13#10 +
    'The AI models are not made or distributed by the author of ArtFlawless Studio: the setup downloads them from their original sources, and each of them is subject to its own licence. ArtFlawless Studio tries to reduce the risk of misuse, but as open-source software it cannot rule it out completely. Anyone who gets around these protections, or changes the program to do so, does it at their own responsibility; the author does not consent to this and accepts no liability for it.' + #13#10 +
    '' + #13#10 +
    'You alone are responsible for what you create and how you use it, including the laws that apply to you and the rights of others. Do not depict real people without their consent.';
  AgeCheck := TNewCheckBox.Create(AgePage);
  AgeCheck.Parent := AgePage.Surface;
  AgeCheck.Left := 0;
  AgeCheck.Top := AgeMemo.Top + AgeMemo.Height + ScaleY(10);
  AgeCheck.Width := AgePage.SurfaceWidth;
  AgeCheck.Height := ScaleY(20);
  AgeCheck.Font.Style := [fsBold];
  if IsHu() then AgeCheck.Caption := 'Kijelentem, hogy elmúltam 18 éves, és a fentieket elfogadom.' else AgeCheck.Caption := 'I declare that I am at least 18 years old, and I accept the above.';
  AgeCheck.OnClick := @AgeCheckClick;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = AgePage.ID then
  begin
    WizardForm.NextButton.Enabled := AgeCheck.Checked;
    if IsHu() then WizardForm.NextButton.Caption := 'Elfogadom' else WizardForm.NextButton.Caption := 'I accept';
  end
  else
    WizardForm.NextButton.Caption := SetupMessage(msgButtonNext);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  FreeMB, TotalMB: Cardinal;
  Drive: String;
begin
  Result := True;
  if (CurPageID = AgePage.ID) and not AgeCheck.Checked then
  begin
    Result := False;
    Exit;
  end;
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
