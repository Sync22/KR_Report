param(
    [string]$TaskPrefix = "StockMonitor",
    [string]$PythonExe = "python",
    [string]$PollStart = "08:30",
    [string]$PollEnd = "16:30",
    [int]$PollIntervalMinutes = 30,
    [string]$NotifyTime = "08:20",
    [string]$KrxDailyBackfillTime = "08:10",
    [string]$KrxDailyBackfillEnd = "08:10",
    [int]$KrxDailyBackfillIntervalMinutes = 60,
    [int]$KrxDailyBackfillLookbackDays = 7,
    [int]$KrxDailyBackfillMaxDates = 3,
    [double]$KrxDailyBackfillSleepSeconds = 3,
    [string]$KrxMentionedFlowBackfillTime = "16:00",
    [int]$KrxMentionedFlowBackfillLookbackDays = 31,
    [int]$KrxMentionedFlowBackfillMentionThreshold = 1,
    [int]$KrxMentionedFlowBackfillMaxCalls = 300,
    [double]$KrxMentionedFlowBackfillSleepSeconds = 1,
    [string]$MarketBriefingMoodTime = "09:15",
    [string]$MarketBriefingLunchTime = "12:00",
    [string]$MarketBriefingPrecloseTime = "15:15",
    [int]$MarketBriefingLimit = 5,
    [string]$TossPriorityBaselineTime = "20:00",
    [string]$TossMarketContextCaptureTime = "15:00",
    [string]$KrxFlowReminderTime = "16:45",
    [string]$KrxFlowPlannedTime = "16:50",
    [int]$KrxFlowReminderMinutesBefore = 5,
    [switch]$IncludeKrxFlowReminder,
    [string]$TelegramCommandStart = "08:00",
    [string]$TelegramCommandEnd = "16:30",
    [int]$TelegramCommandIntervalMinutes = 1,
    [string]$WebViewRestartStart = "00:05",
    [int]$WebViewRestartIntervalHours = 1,
    [string]$ShutdownTime = "17:10",
    [switch]$SkipPoll,
    [switch]$SkipNotify,
    [switch]$SkipKrxDailyBackfill,
    [switch]$SkipKrxMentionedFlowBackfill,
    [switch]$SkipMarketBriefing,
    [switch]$SkipTossPriorityBaseline,
    [switch]$IncludeTossMarketContextCapture,
    [switch]$SkipTelegramCommands,
    [switch]$SkipWebViewRestart,
    [switch]$SkipShutdown
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$pollScript = Join-Path $PSScriptRoot "run_scheduled_poll.ps1"
$notifyScript = Join-Path $PSScriptRoot "run_scheduled_notify.ps1"
$krxDailyBackfillScript = Join-Path $PSScriptRoot "run_scheduled_krx_daily_backfill.ps1"
$krxMentionedFlowBackfillScript = Join-Path $PSScriptRoot "run_scheduled_krx_mentioned_flow_backfill.ps1"
$marketBriefingSlotScript = Join-Path $PSScriptRoot "run_scheduled_market_briefing_slot.ps1"
$tossPriorityBaselineScript = Join-Path $PSScriptRoot "run_scheduled_toss_priority_baseline.ps1"
$tossMarketContextCaptureScript = Join-Path $PSScriptRoot "run_scheduled_toss_market_context_capture.ps1"
$krxFlowReminderScript = Join-Path $PSScriptRoot "run_krx_flow_login_reminder.ps1"
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
$krxDailyBackfillTaskName = "$TaskPrefix-KrxDailyBackfill"
$krxMentionedFlowBackfillTaskName = "$TaskPrefix-KrxMentionedFlowBackfill"
$marketBriefingMoodTaskName = "$TaskPrefix-MarketBriefingMood"
$marketBriefingLunchTaskName = "$TaskPrefix-MarketBriefingLunch"
$marketBriefingPrecloseTaskName = "$TaskPrefix-MarketBriefingPreclose"
$tossPriorityBaselineTaskName = "$TaskPrefix-TossPriorityBaseline"
$tossMarketContextCaptureTaskName = "$TaskPrefix-TossMarketContextCapture"
$krxFlowReminderTaskName = "$TaskPrefix-KrxFlowLoginReminder"
$commandsTaskName = "$TaskPrefix-TelegramCommands"
$webViewRestartTaskName = "$TaskPrefix-WebViewHourlyRestart"
$shutdownTaskName = "$TaskPrefix-Shutdown"

$pollStartTime = [datetime]::ParseExact($PollStart, "HH:mm", $null)
$pollEndTime = [datetime]::ParseExact($PollEnd, "HH:mm", $null)
$telegramCommandStartTime = [datetime]::ParseExact($TelegramCommandStart, "HH:mm", $null)
$telegramCommandEndTime = [datetime]::ParseExact($TelegramCommandEnd, "HH:mm", $null)
$krxDailyBackfillStartTime = [datetime]::ParseExact($KrxDailyBackfillTime, "HH:mm", $null)
$krxDailyBackfillEndTime = [datetime]::ParseExact($KrxDailyBackfillEnd, "HH:mm", $null)

if ($telegramCommandEndTime -lt $telegramCommandStartTime) {
    throw "Telegram command end time must be later than or equal to the start time."
}
if ($krxDailyBackfillEndTime -lt $krxDailyBackfillStartTime) {
    throw "KRX daily backfill end time must be later than or equal to the start time."
}
if ($KrxDailyBackfillIntervalMinutes -lt 1) {
    throw "KRX daily backfill interval must be at least 1 minute."
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

if (-not $SkipKrxDailyBackfill) {
    $krxDailyBackfillAction = New-StockMonitorAction `
        -ScriptPath $krxDailyBackfillScript `
        -PythonCommand $PythonExe `
        -AdditionalArguments "-LookbackDays $KrxDailyBackfillLookbackDays -MaxDates $KrxDailyBackfillMaxDates -SleepSeconds $KrxDailyBackfillSleepSeconds"
    $krxDailyBackfillTriggers = @()
    $probe = $krxDailyBackfillStartTime
    while ($probe -le $krxDailyBackfillEndTime) {
        $krxDailyBackfillTriggers += New-WeekdayTriggerAt -AtTime $probe.ToString("HH:mm")
        $probe = $probe.AddMinutes($KrxDailyBackfillIntervalMinutes)
    }
    Register-OrUpdateTask -TaskName $krxDailyBackfillTaskName -Action $krxDailyBackfillAction -Triggers $krxDailyBackfillTriggers
}

if (-not $SkipKrxMentionedFlowBackfill) {
    $krxMentionedFlowBackfillAction = New-StockMonitorAction `
        -ScriptPath $krxMentionedFlowBackfillScript `
        -PythonCommand $PythonExe `
        -AdditionalArguments "-LookbackDays $KrxMentionedFlowBackfillLookbackDays -MentionThreshold $KrxMentionedFlowBackfillMentionThreshold -MaxCalls $KrxMentionedFlowBackfillMaxCalls -SleepSeconds $KrxMentionedFlowBackfillSleepSeconds"
    $krxMentionedFlowBackfillTriggers = @(New-WeekdayTriggerAt -AtTime $KrxMentionedFlowBackfillTime)
    Register-OrUpdateTask -TaskName $krxMentionedFlowBackfillTaskName -Action $krxMentionedFlowBackfillAction -Triggers $krxMentionedFlowBackfillTriggers -StartWhenAvailable $false
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
    Register-OrUpdateTask -TaskName $tossPriorityBaselineTaskName -Action $tossPriorityBaselineAction -Triggers $tossPriorityBaselineTriggers -StartWhenAvailable $false
}

if ($IncludeTossMarketContextCapture) {
    $tossMarketContextCaptureAction = New-StockMonitorAction `
        -ScriptPath $tossMarketContextCaptureScript `
        -PythonCommand $PythonExe
    $tossMarketContextCaptureTriggers = @(New-WeekdayTriggerAt -AtTime $TossMarketContextCaptureTime)
    Register-OrUpdateTask -TaskName $tossMarketContextCaptureTaskName -Action $tossMarketContextCaptureAction -Triggers $tossMarketContextCaptureTriggers -StartWhenAvailable $false
}

if ($IncludeKrxFlowReminder) {
    $krxFlowReminderAction = New-StockMonitorAction `
        -ScriptPath $krxFlowReminderScript `
        -PythonCommand $PythonExe `
        -AdditionalArguments "-MinutesBefore $KrxFlowReminderMinutesBefore -PlannedTime $KrxFlowPlannedTime"
    $krxFlowReminderTriggers = @(New-WeekdayTriggerAt -AtTime $KrxFlowReminderTime)
    Register-OrUpdateTask -TaskName $krxFlowReminderTaskName -Action $krxFlowReminderAction -Triggers $krxFlowReminderTriggers -StartWhenAvailable $false
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
if (-not $SkipKrxDailyBackfill) {
    Write-Output "- $krxDailyBackfillTaskName"
}
if (-not $SkipKrxMentionedFlowBackfill) {
    Write-Output "- $krxMentionedFlowBackfillTaskName"
}
if (-not $SkipMarketBriefing) {
    Write-Output "- $marketBriefingMoodTaskName"
    Write-Output "- $marketBriefingLunchTaskName"
    Write-Output "- $marketBriefingPrecloseTaskName"
}
if (-not $SkipTossPriorityBaseline) {
    Write-Output "- $tossPriorityBaselineTaskName"
}
if ($IncludeKrxFlowReminder) {
    Write-Output "- $krxFlowReminderTaskName"
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
