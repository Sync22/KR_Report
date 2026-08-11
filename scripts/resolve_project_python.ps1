function Resolve-StockMonitorPython {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$ProjectRoot,
        [string]$PythonExe = "python"
    )

    $venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $venvPython)) {
        throw "Project venv Python is missing: $venvPython. PATH fallback is disabled. Run .\scripts\setup_mini_pc_environment.ps1 first."
    }

    $resolvedVenvPython = (Resolve-Path -LiteralPath $venvPython).Path
    if ($PythonExe -and $PythonExe -ne "python") {
        if (-not (Test-Path -LiteralPath $PythonExe)) {
            throw "Requested Python executable was not found: $PythonExe. Use $resolvedVenvPython."
        }

        $resolvedRequestedPython = (Resolve-Path -LiteralPath $PythonExe).Path
        if ($resolvedRequestedPython -ne $resolvedVenvPython) {
            throw "Scheduler Python must be the project venv: $resolvedVenvPython. PATH fallback is disabled."
        }
    }

    return $resolvedVenvPython
}
