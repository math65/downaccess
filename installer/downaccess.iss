[Setup]
AppName=DownAccess
AppVersion=0.1.20
AppPublisher=math65
AppPublisherURL=https://github.com/math65/downaccess
AppSupportURL=https://github.com/math65/downaccess/issues
AppUpdatesURL=https://github.com/math65/downaccess/releases
DefaultDirName={autopf}\DownAccess
DefaultGroupName=DownAccess
AllowNoIcons=yes
OutputDir=..\installer_output
OutputBaseFilename=DownAccess-Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\DownAccess.exe
; ShowLanguageDialog=no
; Pour l'icône : décommenter quand assets/icon.ico sera créé
; SetupIconFile=..\assets\icon.ico

[Languages]
Name: "french";  MessagesFile: "compiler:Languages\French.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
french.DesktopIcon=Créer un raccourci sur le Bureau
english.DesktopIcon=Create a desktop shortcut

french.StartMenuIcon=Créer un raccourci dans le menu Démarrer
english.StartMenuIcon=Create a Start menu shortcut

french.ShortcutsGroup=Raccourcis supplémentaires :
english.ShortcutsGroup=Additional shortcuts:

french.AppComment=Téléchargeur vidéo/audio accessible NVDA
english.AppComment=NVDA-accessible video/audio downloader

french.UninstallShortcut=Désinstaller DownAccess
english.UninstallShortcut=Uninstall DownAccess

french.LaunchApp=Lancer DownAccess
english.LaunchApp=Launch DownAccess

[Tasks]
Name: "desktopicon";   Description: "{cm:DesktopIcon}";   GroupDescription: "{cm:ShortcutsGroup}"; Flags: unchecked
Name: "startmenuicon"; Description: "{cm:StartMenuIcon}"; GroupDescription: "{cm:ShortcutsGroup}"; Flags: checkedonce

[Files]
; Application principale
Source: "..\dist\DownAccess\DownAccess.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\DownAccess\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\DownAccess";                Filename: "{app}\DownAccess.exe"; Comment: "{cm:AppComment}"
Name: "{group}\{cm:UninstallShortcut}";    Filename: "{uninstallexe}"
Name: "{userdesktop}\DownAccess";          Filename: "{app}\DownAccess.exe"; Comment: "{cm:AppComment}"; Tasks: desktopicon

[Run]
; Installation manuelle : case "Lancer DownAccess" sur la derniere page de l'assistant
Filename: "{app}\DownAccess.exe"; Description: "{cm:LaunchApp}"; Flags: nowait postinstall skipifsilent
; Mise a jour silencieuse (auto-update /SILENT) : relancer l'app automatiquement
Filename: "{app}\DownAccess.exe"; Flags: nowait skipifnotsilent

[UninstallDelete]
; Supprimer les fichiers créés au runtime (cache yt-dlp, logs…)
Type: filesandordirs; Name: "{app}\_internal\__pycache__"
