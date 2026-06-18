param(
    [string]$TaskPrefix = "StockMonitor",
    [string]$PythonExe = "",
    [switch]$IncludeShutdown,
    [switch]$IncludeKrxFlowReminder
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot

function Test-TaskSchedulerAccessDenied {
    param([string]$Message)

    if ($Message -like "*액세스가 거부*" -or $Message -like "*0x80070005*" -or $Message -like "*0x80041003*" -or $Message -like "*PermissionDenied*") {
        return $true
    }

    return (
        $Message -like "*Access is denied*" -or
        $Message -like "*액세스가 거부*" -or
        $Message -like "*UnauthorizedAccess*"
    )
}

function Get-ExpectedScheduledTask {
    param([string]$TaskName)

    try {
        return Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
    }
    catch {
        $message = "$($_.Exception.Message) $($_.FullyQualifiedErrorId)"
        if (Test-TaskSchedulerAccessDenied -Message $message) {
            Write-Error (
                "Task Scheduler metadata access denied while checking $TaskName. " +
                "Run this verifier from an elevated local PowerShell session."
            )
            exit 1
        }
        return $null
    }
}

function Get-ExpectedScheduledTaskInfo {
    param([string]$TaskName)

    try {
        return Get-ScheduledTaskInfo -TaskName $TaskName -ErrorAction Stop
    }
    catch {
        $message = "$($_.Exception.Message) $($_.FullyQualifiedErrorId)"
        if (Test-TaskSchedulerAccessDenied -Message $message) {
            Write-Error (
                "Task Scheduler metadata access denied while reading $TaskName. " +
                "Run this verifier from an elevated local PowerShell session."
            )
            exit 1
        }
        Write-Error "Unable to read scheduler task info for ${TaskName}: $($_.Exception.Message)"
        exit 1
    }
}

# Default task names:
# - StockMonitor-KrxDailyBackfill
# - StockMonitor-Notify
# - StockMonitor-Poll
# - StockMonitor-KrxMentionedFlowBackfill
# - StockMonitor-MarketBriefingMood
# - StockMonitor-MarketBriefingLunch
# - StockMonitor-MarketBriefingPreclose
# - StockMonitor-TelegramCommands
# - StockMonitor-WebViewHourlyRestart
# - StockMonitor-KrxFlowLoginReminder
$expectedTasks = @(
    @{ Name = "$TaskPrefix-KrxDailyBackfill"; Script = "run_scheduled_krx_daily_backfill.ps1" },
    @{ Name = "$TaskPrefix-Notify"; Script = "run_scheduled_notify.ps1" },
    @{ Name = "$TaskPrefix-Poll"; Script = "run_scheduled_poll.ps1" },
    @{ Name = "$TaskPrefix-KrxMentionedFlowBackfill"; Script = "run_scheduled_krx_mentioned_flow_backfill.ps1" },
    @{ Name = "$TaskPrefix-MarketBriefingMood"; Script = "run_scheduled_market_briefing_slot.ps1" },
    @{ Name = "$TaskPrefix-MarketBriefingLunch"; Script = "run_scheduled_market_briefing_slot.ps1" },
    @{ Name = "$TaskPrefix-MarketBriefingPreclose"; Script = "run_scheduled_market_briefing_slot.ps1" },
    @{ Name = "$TaskPrefix-TelegramCommands"; Script = "run_process_telegram_commands.ps1" },
    @{ Name = "$TaskPrefix-WebViewHourlyRestart"; Script = "restart_web_view.ps1" }
)

if ($IncludeKrxFlowReminder) {
    $expectedTasks += @{ Name = "$TaskPrefix-KrxFlowLoginReminder"; Script = "run_krx_flow_login_reminder.ps1" }
}

if ($IncludeShutdown) {
    # Desktop validation task:
    # - StockMonitor-Shutdown
    $expectedTasks += @{ Name = "$TaskPrefix-Shutdown"; Script = "run_scheduled_shutdown.ps1" }
}
else {
    $unexpectedShutdownTaskName = "$TaskPrefix-Shutdown"
    $unexpectedShutdownTask = Get-ExpectedScheduledTask -TaskName $unexpectedShutdownTaskName
    if ($null -ne $unexpectedShutdownTask) {
        Write-Error (
            "Unexpected desktop validation shutdown task is registered: $unexpectedShutdownTaskName. " +
            "Use -IncludeShutdown only for desktop validation, or disable/delete this task for mini PC always-on operation."
        )
        exit 1
    }
}

$missing = @()
$invalid = @()

foreach ($expected in $expectedTasks) {
    $taskName = [string]$expected.Name
    $scriptName = [string]$expected.Script
    $task = Get-ExpectedScheduledTask -TaskName $taskName
    if ($null -eq $task) {
        $missing += $taskName
        continue
    }

    $taskInfo = Get-ExpectedScheduledTaskInfo -TaskName $taskName
    $actionText = ($task.Actions | ForEach-Object { "$($_.Execute) $($_.Arguments)" }) -join " "
    $expectedScriptPath = Join-Path $projectRoot "scripts\$scriptName"

    if ($actionText -notlike "*$scriptName*") {
        $invalid += "$taskName action does not reference $scriptName"
    }
    if ($actionText -notlike "*$expectedScriptPath*") {
        $invalid += "$taskName action does not reference project script path $expectedScriptPath"
    }
    if ($PythonExe -and $actionText -notlike "*$PythonExe*") {
        $invalid += "$taskName action does not reference PythonExe $PythonExe"
    }

    Write-Output "- ${taskName}: $($task.State); last_result=$($taskInfo.LastTaskResult); script=$scriptName"
}

if ($missing.Count -gt 0) {
    Write-Error "Missing scheduler tasks: $($missing -join ', ')"
    exit 1
}

if ($invalid.Count -gt 0) {
    Write-Error "Invalid scheduler task registration: $($invalid -join '; ')"
    exit 1
}

Write-Output "Task scheduler registration verified."
Write-Output "- expected_tasks: $($expectedTasks.Count)"
if ($PythonExe) {
    Write-Output "- python_exe: $PythonExe"
}
