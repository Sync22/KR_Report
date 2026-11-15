function Test-ScheduledTaskContract {
    param(
        [object]$Task,
        [object]$Expected
    )

    $issues = @()
    if (-not $Task.Settings.Enabled -or $Task.State -eq "Disabled") {
        $issues += "task is disabled"
    }
    $triggers = @($Task.Triggers)
    if ($triggers.Count -eq 0 -or @($triggers | Where-Object { -not $_.Enabled }).Count -gt 0) {
        $issues += "task has a disabled or missing trigger"
        return $issues
    }

    if ($Expected.Type -eq "weekly") {
        $times = @()
        foreach ($trigger in $triggers) {
            if ($trigger.CimClass.CimClassName -ne "MSFT_TaskWeeklyTrigger" -or
                [int]$trigger.DaysOfWeek -ne 62 -or [int]$trigger.WeeksInterval -ne 1) {
                $issues += "weekly trigger weekdays or interval differ"
                continue
            }
            $boundary = [datetime]::MinValue
            if (-not [datetime]::TryParse([string]$trigger.StartBoundary, [ref]$boundary)) {
                $issues += "weekly trigger start boundary is invalid"
                continue
            }
            if ($boundary.Second -ne 0 -or $boundary.Millisecond -ne 0) {
                $issues += "weekly trigger seconds must be zero"
            }
            if ($trigger.EndBoundary) {
                $issues += "weekly trigger must not have an end boundary"
            }
            if ($trigger.RandomDelay) {
                try {
                    if ([System.Xml.XmlConvert]::ToTimeSpan($trigger.RandomDelay) -ne [TimeSpan]::Zero) {
                        $issues += "weekly trigger must not have random delay"
                    }
                }
                catch {
                    $issues += "weekly trigger random delay is invalid"
                }
            }
            if ($trigger.Repetition.Interval -or $trigger.Repetition.Duration -or $trigger.Repetition.StopAtDurationEnd) {
                $issues += "weekly trigger must not repeat"
            }
            $times += $boundary.ToString("HH:mm")
        }
        $actualTimes = @($times | Sort-Object) -join ","
        $expectedTimes = @($Expected.Times | Sort-Object) -join ","
        if ($actualTimes -cne $expectedTimes) {
            $issues += "weekly trigger times differ"
        }
        return $issues
    }

    if ($Expected.Type -eq "hourly") {
        if ($triggers.Count -ne 1 -or $triggers[0].CimClass.CimClassName -notin @("MSFT_TaskTimeTrigger", "MSFT_TaskDailyTrigger")) {
            $issues += "hourly trigger type differs"
            return $issues
        }
        $trigger = $triggers[0]
        $boundary = [datetime]::MinValue
        if (-not [datetime]::TryParse([string]$trigger.StartBoundary, [ref]$boundary)) {
            $issues += "hourly trigger start boundary is invalid"
            return $issues
        }
        if ($boundary.Second -ne 0 -or $boundary.Millisecond -ne 0 -or $boundary.ToString("HH:mm") -cne $Expected.Start) {
            $issues += "hourly trigger start differs"
        }
        if ($trigger.RandomDelay) {
            try {
                if ([System.Xml.XmlConvert]::ToTimeSpan($trigger.RandomDelay) -ne [TimeSpan]::Zero) {
                    $issues += "hourly trigger must not have random delay"
                }
            }
            catch {
                $issues += "hourly trigger random delay is invalid"
            }
        }
        if ($trigger.Repetition.Interval -cne $Expected.Interval) {
            $issues += "hourly repetition differs"
        }
        if ($trigger.CimClass.CimClassName -eq "MSFT_TaskTimeTrigger" -and
            ($trigger.Repetition.Duration -or $trigger.EndBoundary -or $trigger.Repetition.StopAtDurationEnd)) {
            $issues += "hourly time trigger must repeat indefinitely"
        }
        if ($trigger.CimClass.CimClassName -eq "MSFT_TaskDailyTrigger") {
            if ($trigger.EndBoundary) {
                $issues += "hourly daily trigger must not have an end boundary"
            }
            if ([int]$trigger.DaysInterval -ne 1) {
                $issues += "hourly daily trigger must recur every day"
            }
            if ($trigger.Repetition.Duration) {
                try {
                    if ([System.Xml.XmlConvert]::ToTimeSpan($trigger.Repetition.Duration) -le [TimeSpan]::FromHours(23)) {
                        $issues += "hourly daily repetition duration is too short"
                    }
                }
                catch {
                    $issues += "hourly daily repetition duration is invalid"
                }
            }
            if ($trigger.Repetition.StopAtDurationEnd) {
                $issues += "hourly daily repetition must not stop a running task at its duration end"
            }
        }
        return $issues
    }

    $issues += "unknown schedule contract"
    return $issues
}
