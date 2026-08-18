param(
    [string]$TaskPrefix = "StockMonitor",
    [string]$PythonExe = "python",
    [string]$PollStart = "08:30",
    [string]$PollEnd = "16:30",
    [int]$PollIntervalMinutes = 30,
    [string]$NotifyTime = "08:20",
    [string]$MarketBriefingMoodTime = "09:15",
    [string]$MarketBriefingLunchTime = "12:00",
    [string]$MarketBriefingPrecloseTime = "15:15",
    [int]$MarketBriefingLimit = 5,
    [string]$TossPriorityBaselineTime = "20:00",
    [string]$TelegramCommandStart = "08:00",
    [string]$TelegramCommandEnd = "16:30",
    [int]$TelegramCommandIntervalMinutes = 1,
    [string]$WebViewRestartStart = "00:05",
    [int]$WebViewRestartIntervalHours = 1,
    [string]$ShutdownTime = "17:10",
    [switch]$SkipPoll,
    [switch]$SkipNotify,
    [switch]$SkipMarketBriefing,
    [switch]$SkipTossPriorityBaseline,
    [switch]$SkipTelegramCommands,
    [switch]$SkipWebViewRestart,
    [switch]$SkipShutdown
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "resolve_project_python.ps1")
$PythonExe = Resolve-StockMonitorPython -ProjectRoot $projectRoot -PythonExe $PythonExe
$pollScript = Join-Path $PSScriptRoot "run_scheduled_poll.ps1"
$notifyScript = Join-Path $PSScriptRoot "run_scheduled_notify.ps1"
$marketBriefingSlotScript = Join-Path $PSScriptRoot "run_scheduled_market_briefing_slot.ps1"
$tossPriorityBaselineScript = Join-Path $PSScriptRoot "run_scheduled_toss_priority_baseline.ps1"
$commandsScript = Join-Path $PSScriptRoot "run_process_telegram_commands.ps1"
$webViewRestartScript = Join-Path $PSScriptRoot "restart_web_view.ps1"
$shutdownScript = Join-Path $PSScriptRoot "run_scheduled_shutdown.ps1"

function New-StockMonitorAction(
    [string]$ScriptPath,
    [string]$PythonCommand,
    [string]$AdditionalArguments = ""
) {
    $arguments = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$ScriptPath`" -PythonExe `"$PythonCommand`""
    if ($AdditionalArguments) {
        $arguments = "$arguments $AdditionalArguments"
    }
    New-ScheduledTaskAction `
        -Execute "powershell.exe" `
        -Argument $arguments
}

function New-WeekdayTriggerAt([string]$AtTime) {
    New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At $AtTime
}

function Register-OrUpdateTask(
    [string]$TaskName,
    [Microsoft.Management.Infrastructure.CimInstance]$Action,
    [Microsoft.Management.Infrastructure.CimInstance[]]$Triggers,
    [bool]$StartWhenAvailable = $true
) {
    if ($StartWhenAvailable) {
        $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    }
    else {
        $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    }
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Triggers -Settings $settings -Force | Out-Null
}

function Remove-LegacyTask([string]$TaskName) {
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($null -ne $task) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Output "Removed legacy task: $TaskName"
    }
}

function Register-RepeatingWeekdayTask(
    [string]$TaskName,
    [string]$ScriptPath,
    [string]$PythonCommand,
    [string]$StartTime,
    [string]$Duration,
    [int]$RepeatIntervalMinutes
) {
    $taskRunCommand = "powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$ScriptPath`" -PythonExe `"$PythonCommand`""
    schtasks.exe /Create `
        /TN $TaskName `
        /TR $taskRunCommand `
        /SC WEEKLY `
        /MO 1 `
        /D MON,TUE,WED,THU,FRI `
        /ST $StartTime `
        /RI $RepeatIntervalMinutes `
        /DU $Duration `
        /F | Out-Null
}

function Register-HourlyTask(
    [string]$TaskName,
    [string]$ScriptPath,
    [string]$PythonCommand,
    [string]$StartTime,
    [int]$RepeatIntervalHours
) {
    $taskRunCommand = "powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$ScriptPath`" -PythonExe `"$PythonCommand`""
    schtasks.exe /Create `
        /TN $TaskName `
        /TR $taskRunCommand `
        /SC HOURLY `
        /MO $RepeatIntervalHours `
        /ST $StartTime `
        /F | Out-Null
}

$pollTaskName = "$TaskPrefix-Poll"
$notifyTaskName = "$TaskPrefix-Notify"
$marketBriefingMoodTaskName = "$TaskPrefix-MarketBriefingMood"
$marketBriefingLunchTaskName = "$TaskPrefix-MarketBriefingLunch"
$marketBriefingPrecloseTaskName = "$TaskPrefix-MarketBriefingPreclose"
$tossCloseSnapshotTaskName = "$TaskPrefix-TossCloseSnapshot"
$commandsTaskName = "$TaskPrefix-TelegramCommands"
$webViewRestartTaskName = "$TaskPrefix-WebViewHourlyRestart"
$shutdownTaskName = "$TaskPrefix-Shutdown"

Remove-LegacyTask -TaskName "$TaskPrefix-KrxDailyBackfill"
Remove-LegacyTask -TaskName "$TaskPrefix-KrxMentionedFlowBackfill"
Remove-LegacyTask -TaskName "$TaskPrefix-KrxFlowLoginReminder"
Remove-LegacyTask -TaskName "$TaskPrefix-TossMarketContextCapture"
Remove-LegacyTask -TaskName "$TaskPrefix-TossPriorityBaseline"

$pollStartTime = [datetime]::ParseExact($PollStart, "HH:mm", $null)
$pollEndTime = [datetime]::ParseExact($PollEnd, "HH:mm", $null)
$telegramCommandStartTime = [datetime]::ParseExact($TelegramCommandStart, "HH:mm", $null)
$telegramCommandEndTime = [datetime]::ParseExact($TelegramCommandEnd, "HH:mm", $null)

if ($telegramCommandEndTime -lt $telegramCommandStartTime) {
    throw "Telegram command end time must be later than or equal to the start time."
}

$telegramCommandDuration = $telegramCommandEndTime - $telegramCommandStartTime
$telegramCommandDurationString = "{0:00}:{1:00}" -f [int]$telegramCommandDuration.TotalHours, $telegramCommandDuration.Minutes

if (-not $SkipPoll) {
    $pollAction = New-StockMonitorAction -ScriptPath $pollScript -PythonCommand $PythonExe
    $pollTriggers = @()
    $probe = $pollStartTime
    while ($probe -le $pollEndTime) {
        $pollTriggers += New-WeekdayTriggerAt -AtTime $probe.ToString("HH:mm")
        $probe = $probe.AddMinutes($PollIntervalMinutes)
    }
    Register-OrUpdateTask -TaskName $pollTaskName -Action $pollAction -Triggers $pollTriggers
}

if (-not $SkipNotify) {
    $notifyAction = New-StockMonitorAction -ScriptPath $notifyScript -PythonCommand $PythonExe
    $notifyTriggers = @(New-WeekdayTriggerAt -AtTime $NotifyTime)
    Register-OrUpdateTask -TaskName $notifyTaskName -Action $notifyAction -Triggers $notifyTriggers
}


if (-not $SkipMarketBriefing) {
    $marketBriefingMoodAction = New-StockMonitorAction `
        -ScriptPath $marketBriefingSlotScript `
        -PythonCommand $PythonExe `
        -AdditionalArguments "-Slot mood -Limit $MarketBriefingLimit"
    $marketBriefingMoodTriggers = @(New-WeekdayTriggerAt -AtTime $MarketBriefingMoodTime)
    Register-OrUpdateTask -TaskName $marketBriefingMoodTaskName -Action $marketBriefingMoodAction -Triggers $marketBriefingMoodTriggers -StartWhenAvailable $false

    $marketBriefingLunchAction = New-StockMonitorAction `
        -ScriptPath $marketBriefingSlotScript `
        -PythonCommand $PythonExe `
        -AdditionalArguments "-Slot lunch -Limit $MarketBriefingLimit"
    $marketBriefingLunchTriggers = @(New-WeekdayTriggerAt -AtTime $MarketBriefingLunchTime)
    Register-OrUpdateTask -TaskName $marketBriefingLunchTaskName -Action $marketBriefingLunchAction -Triggers $marketBriefingLunchTriggers -StartWhenAvailable $false

    $marketBriefingPrecloseAction = New-StockMonitorAction `
        -ScriptPath $marketBriefingSlotScript `
        -PythonCommand $PythonExe `
        -AdditionalArguments "-Slot preclose -Limit $MarketBriefingLimit"
    $marketBriefingPrecloseTriggers = @(New-WeekdayTriggerAt -AtTime $MarketBriefingPrecloseTime)
    Register-OrUpdateTask -TaskName $marketBriefingPrecloseTaskName -Action $marketBriefingPrecloseAction -Triggers $marketBriefingPrecloseTriggers -StartWhenAvailable $false
}

if (-not $SkipTossPriorityBaseline) {
    $tossPriorityBaselineAction = New-StockMonitorAction `
        -ScriptPath $tossPriorityBaselineScript `
        -PythonCommand $PythonExe
    $tossPriorityBaselineTriggers = @(New-WeekdayTriggerAt -AtTime $TossPriorityBaselineTime)
    Register-OrUpdateTask -TaskName $tossCloseSnapshotTaskName -Action $tossPriorityBaselineAction -Triggers $tossPriorityBaselineTriggers -StartWhenAvailable $false
}


if (-not $SkipTelegramCommands) {
    $commandsAction = New-StockMonitorAction `
        -ScriptPath $commandsScript `
        -PythonCommand $PythonExe `
        -AdditionalArguments "-EndTime $TelegramCommandEnd -IntervalSeconds $($TelegramCommandIntervalMinutes * 60)"
    $commandsTriggers = @(New-WeekdayTriggerAt -AtTime $TelegramCommandStart)
    Register-OrUpdateTask -TaskName $commandsTaskName -Action $commandsAction -Triggers $commandsTriggers
}

if (-not $SkipWebViewRestart) {
    Register-HourlyTask `
        -TaskName $webViewRestartTaskName `
        -ScriptPath $webViewRestartScript `
        -PythonCommand $PythonExe `
        -StartTime $WebViewRestartStart `
        -RepeatIntervalHours $WebViewRestartIntervalHours
}

if (-not $SkipShutdown) {
    $shutdownAction = New-StockMonitorAction -ScriptPath $shutdownScript -PythonCommand $PythonExe
    $shutdownTriggers = @(New-WeekdayTriggerAt -AtTime $ShutdownTime)
    Register-OrUpdateTask -TaskName $shutdownTaskName -Action $shutdownAction -Triggers $shutdownTriggers -StartWhenAvailable $false
}

Write-Output "Registered tasks:"
if (-not $SkipPoll) {
    Write-Output "- $pollTaskName"
}
if (-not $SkipNotify) {
    Write-Output "- $notifyTaskName"
}
if (-not $SkipMarketBriefing) {
    Write-Output "- $marketBriefingMoodTaskName"
    Write-Output "- $marketBriefingLunchTaskName"
    Write-Output "- $marketBriefingPrecloseTaskName"
}
if (-not $SkipTossPriorityBaseline) {
    Write-Output "- $tossCloseSnapshotTaskName"
}
if (-not $SkipTelegramCommands) {
    Write-Output "- $commandsTaskName"
}
if (-not $SkipWebViewRestart) {
    Write-Output "- $webViewRestartTaskName"
}
if (-not $SkipShutdown) {
    Write-Output "- $shutdownTaskName"
}
