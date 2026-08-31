[CmdletBinding()]
param(
    [string]$Python,
    [switch]$DesktopShortcut,
    [switch]$Uninstall,
    [switch]$NoDialog
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Launcher = Join-Path $Root "launch-workflow-configurator.ps1"
$DataRoot = if ($env:WORKFLOW_CONFIGURATOR_DATA_HOME) {
    $env:WORKFLOW_CONFIGURATOR_DATA_HOME
} else {
    Join-Path ([Environment]::GetFolderPath("LocalApplicationData")) "workflow-configurator"
}
$StartMenuDirectory = if ($env:WORKFLOW_CONFIGURATOR_START_MENU_HOME) {
    $env:WORKFLOW_CONFIGURATOR_START_MENU_HOME
} else {
    Join-Path (
        [Environment]::GetFolderPath("ApplicationData")
    ) "Microsoft\Windows\Start Menu\Programs"
}
$DesktopDirectory = [Environment]::GetFolderPath("Desktop")
$ConfigFile = Join-Path $DataRoot "python-interpreter"
$StartMenuShortcut = Join-Path $StartMenuDirectory "Workflow Configurator.lnk"
$DesktopLink = if ($DesktopDirectory) {
    Join-Path $DesktopDirectory "Workflow Configurator.lnk"
} else {
    $null
}

function Show-InstallerMessage {
    param(
        [string]$Message,
        [bool]$ErrorMessage = $false
    )

    if ($NoDialog) {
        if ($ErrorMessage) {
            [Console]::Error.WriteLine($Message)
        } else {
            Write-Output $Message
        }
        return
    }
    try {
        Add-Type -AssemblyName PresentationFramework
        $icon = if ($ErrorMessage) {
            [System.Windows.MessageBoxImage]::Error
        } else {
            [System.Windows.MessageBoxImage]::Information
        }
        [System.Windows.MessageBox]::Show(
            $Message,
            "Workflow Configurator",
            [System.Windows.MessageBoxButton]::OK,
            $icon
        ) | Out-Null
    } catch {
        if ($ErrorMessage) {
            [Console]::Error.WriteLine($Message)
        } else {
            Write-Output $Message
        }
    }
}

function New-UserShortcut {
    param([string]$Path)

    [IO.Directory]::CreateDirectory((Split-Path -Parent $Path)) | Out-Null
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $null
    try {
        $shortcut = $shell.CreateShortcut($Path)
        $powerShell = (Get-Process -Id $PID).Path
        $shortcut.TargetPath = $powerShell
        $shortcut.Arguments = (
            '-NoLogo -NoProfile -WindowStyle Hidden -File "' +
            $Launcher.Replace('"', '""') +
            '"'
        )
        $shortcut.WorkingDirectory = $Root
        $shortcut.Description = (
            "Safely configure workflow_configurator for new or existing projects"
        )
        $shortcut.IconLocation = (
            (Join-Path $env:SystemRoot "System32\shell32.dll") + ",167"
        )
        $shortcut.Save()
    } finally {
        if ($shortcut) {
            [Runtime.InteropServices.Marshal]::FinalReleaseComObject(
                $shortcut
            ) | Out-Null
        }
        [Runtime.InteropServices.Marshal]::FinalReleaseComObject(
            $shell
        ) | Out-Null
    }
}

try {
    if ($Uninstall) {
        Remove-Item -LiteralPath $StartMenuShortcut -Force `
            -ErrorAction SilentlyContinue
        if ($DesktopLink) {
            Remove-Item -LiteralPath $DesktopLink -Force `
                -ErrorAction SilentlyContinue
        }
        Remove-Item -LiteralPath $ConfigFile -Force `
            -ErrorAction SilentlyContinue
        Show-InstallerMessage "Workflow Configurator user shortcuts were removed."
        exit 0
    }

    if (-not (Test-Path -LiteralPath $Launcher -PathType Leaf)) {
        throw "Windows launcher is missing: $Launcher"
    }

    $previousPython = $env:WORKFLOW_CONFIGURATOR_PYTHON
    try {
        if ($Python) {
            $env:WORKFLOW_CONFIGURATOR_PYTHON = $Python
        }
        $output = @(& $Launcher -PrintInterpreter)
        if ($LASTEXITCODE -ne 0) {
            throw "The selected Python interpreter failed launcher validation"
        }
        $selectedPython = $output |
            ForEach-Object { "$_".Trim() } |
            Where-Object { $_ } |
            Select-Object -Last 1
    } finally {
        $env:WORKFLOW_CONFIGURATOR_PYTHON = $previousPython
    }
    if (-not $selectedPython) {
        throw "The launcher did not return a Python executable"
    }

    [IO.Directory]::CreateDirectory($DataRoot) | Out-Null
    if (Test-Path -LiteralPath $ConfigFile) {
        $configItem = Get-Item -LiteralPath $ConfigFile -Force
        if ($configItem.Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw "Refusing reparse-point interpreter configuration: $ConfigFile"
        }
    }
    $temporary = Join-Path $DataRoot (
        ".python-interpreter." + [Guid]::NewGuid().ToString("N") + ".tmp"
    )
    try {
        $encoding = New-Object Text.UTF8Encoding($false)
        [IO.File]::WriteAllText(
            $temporary,
            $selectedPython + [Environment]::NewLine,
            $encoding
        )
        Move-Item -LiteralPath $temporary -Destination $ConfigFile -Force
    } finally {
        Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue
    }

    New-UserShortcut $StartMenuShortcut
    if ($DesktopShortcut -and $DesktopLink) {
        New-UserShortcut $DesktopLink
    }

    $message = (
        "Workflow Configurator was installed for the current user.`n`n" +
        "Python: $selectedPython`n" +
        "Start Menu: $StartMenuShortcut"
    )
    if ($DesktopShortcut -and $DesktopLink) {
        $message += "`nDesktop: $DesktopLink"
    }
    Show-InstallerMessage $message
    exit 0
} catch {
    Show-InstallerMessage $_.Exception.Message $true
    exit 1
}
