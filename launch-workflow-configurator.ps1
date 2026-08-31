[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$Target,
    [switch]$HeadlessSmoke,
    [switch]$PrintInterpreter,
    [switch]$Wait
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$DataRoot = if ($env:WORKFLOW_CONFIGURATOR_DATA_HOME) {
    $env:WORKFLOW_CONFIGURATOR_DATA_HOME
} else {
    Join-Path ([Environment]::GetFolderPath("LocalApplicationData")) "workflow-configurator"
}
$ConfigFile = Join-Path $DataRoot "python-interpreter"
$LegacyConfigFile = Join-Path (
    [Environment]::GetFolderPath("LocalApplicationData")
) "template-gpt\python-interpreter"
$LogDirectory = Join-Path $DataRoot "logs"

function Show-LauncherError {
    param([string]$Message)

    try {
        Add-Type -AssemblyName PresentationFramework
        [System.Windows.MessageBox]::Show(
            $Message,
            "Workflow Configurator",
            [System.Windows.MessageBoxButton]::OK,
            [System.Windows.MessageBoxImage]::Error
        ) | Out-Null
    } catch {
        [Console]::Error.WriteLine("Workflow Configurator: $Message")
    }
}

function Resolve-PythonCommand {
    param(
        [string]$Command,
        [string[]]$PrefixArguments,
        [string]$Source,
        [switch]$Required
    )

    try {
        $output = @(
            & $Command @PrefixArguments -c "import sys; print(sys.executable)" 2>$null
        )
        if ($LASTEXITCODE -ne 0) {
            throw "command exited with code $LASTEXITCODE"
        }
        $path = $output |
            ForEach-Object { "$_".Trim() } |
            Where-Object { $_ } |
            Select-Object -Last 1
        if (-not $path -or -not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "command did not return an executable Python path"
        }
        return [PSCustomObject]@{
            Path = [IO.Path]::GetFullPath($path)
            Source = $Source
        }
    } catch {
        if ($Required) {
            throw "Cannot use Python from ${Source}: $($_.Exception.Message)"
        }
        return $null
    }
}

function Resolve-DirectPython {
    param(
        [string]$Path,
        [string]$Source,
        [switch]$Required
    )

    if (-not $Path -or -not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        if ($Required) {
            throw "Python executable is unavailable: $Path"
        }
        return $null
    }
    return Resolve-PythonCommand -Command $Path -PrefixArguments @() `
        -Source $Source -Required:$Required
}

function Quote-ProcessArgument {
    param([string]$Value)

    if ($Value -notmatch '[\s"]') {
        return $Value
    }
    $escaped = $Value.Replace('"', '\"')
    if ($escaped.EndsWith("\")) {
        $escaped += "\"
    }
    return '"' + $escaped + '"'
}

function Resolve-ConfiguratorPython {
    if ($env:WORKFLOW_CONFIGURATOR_PYTHON) {
        return Resolve-DirectPython -Path $env:WORKFLOW_CONFIGURATOR_PYTHON `
            -Source "WORKFLOW_CONFIGURATOR_PYTHON" -Required
    }

    $directCandidates = @(
        [PSCustomObject]@{
            Base = $env:VIRTUAL_ENV
            Relative = "Scripts\python.exe"
            Source = "active virtual environment"
        },
        [PSCustomObject]@{
            Base = $env:CONDA_PREFIX
            Relative = "python.exe"
            Source = "active Conda environment"
        },
        [PSCustomObject]@{
            Base = $Root
            Relative = ".venv\Scripts\python.exe"
            Source = "repository .venv"
        },
        [PSCustomObject]@{
            Base = $Root
            Relative = ".conda\python.exe"
            Source = "repository .conda"
        }
    )
    foreach ($candidate in $directCandidates) {
        if (-not $candidate.Base) {
            continue
        }
        $path = Join-Path $candidate.Base $candidate.Relative
        if (Test-Path -LiteralPath $path -PathType Leaf) {
            return Resolve-DirectPython -Path $path -Source $candidate.Source `
                -Required
        }
    }

    if ($env:WORKFLOW_CONFIGURATOR_ENV) {
        $conda = if ($env:CONDA_EXE) {
            $env:CONDA_EXE
        } else {
            $command = Get-Command conda.exe, conda.bat, conda `
                -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($command) { $command.Source } else { $null }
        }
        if (-not $conda) {
            throw "WORKFLOW_CONFIGURATOR_ENV is set, but Conda is unavailable"
        }
        return Resolve-PythonCommand -Command $conda -PrefixArguments @(
            "run",
            "--no-capture-output",
            "-n",
            $env:WORKFLOW_CONFIGURATOR_ENV,
            "python"
        ) -Source "explicit Conda environment" -Required
    }

    if (Test-Path -LiteralPath $ConfigFile -PathType Leaf) {
        $saved = [IO.File]::ReadAllText($ConfigFile).Trim()
        return Resolve-DirectPython -Path $saved -Source "saved Start Menu choice" `
            -Required
    }
    if (Test-Path -LiteralPath $LegacyConfigFile -PathType Leaf) {
        $saved = [IO.File]::ReadAllText($LegacyConfigFile).Trim()
        return Resolve-DirectPython -Path $saved `
            -Source "legacy saved Start Menu choice" -Required
    }

    $py = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($py) {
        $resolved = Resolve-PythonCommand -Command $py.Source `
            -PrefixArguments @("-3") -Source "Python launcher"
        if ($resolved) {
            return $resolved
        }
    }

    $python = Get-Command python.exe, python -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($python) {
        return Resolve-PythonCommand -Command $python.Source `
            -PrefixArguments @() -Source "PATH Python" -Required
    }
    throw "No Python interpreter was found"
}

try {
    $selection = Resolve-ConfiguratorPython
    $python = $selection.Path

    & $python -c "import PySide6" 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw (
            "PySide6 is not installed in the selected environment.`n`n" +
            "Python: $python`nSource: $($selection.Source)`n`n" +
            "Install workflow_configurator\requirements-gui.txt in that environment, " +
            "or set WORKFLOW_CONFIGURATOR_PYTHON to another interpreter."
        )
    }

    if ($PrintInterpreter) {
        Write-Output $python
        exit 0
    }

    $targetPath = if ($Target) {
        [IO.Path]::GetFullPath($Target)
    } else {
        $Root
    }
    $gui = Join-Path $Root "workflow_configurator\gui.py"
    if ($HeadlessSmoke) {
        & $python $gui --headless-smoke $targetPath
        exit $LASTEXITCODE
    }

    [IO.Directory]::CreateDirectory($LogDirectory) | Out-Null
    $stdoutLog = Join-Path $LogDirectory "configurator.out.log"
    $stderrLog = Join-Path $LogDirectory "configurator.err.log"
    $installer = Join-Path $Root "workflow_configurator\install.py"
    $windowlessPython = Join-Path (Split-Path -Parent $python) "pythonw.exe"
    $launchPython = if (Test-Path -LiteralPath $windowlessPython -PathType Leaf) {
        $windowlessPython
    } else {
        $python
    }
    $arguments = @(
        (Quote-ProcessArgument $installer),
        "--gui",
        (Quote-ProcessArgument $targetPath)
    )
    $process = Start-Process -FilePath $launchPython `
        -ArgumentList $arguments `
        -WorkingDirectory $Root `
        -WindowStyle Hidden `
        -RedirectStandardOutput $stdoutLog `
        -RedirectStandardError $stderrLog `
        -PassThru
    if ($Wait) {
        $process.WaitForExit()
        exit $process.ExitCode
    }
    exit 0
} catch {
    Show-LauncherError $_.Exception.Message
    exit 1
}
