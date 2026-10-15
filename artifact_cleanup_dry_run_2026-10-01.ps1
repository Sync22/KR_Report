# 실행 확인: PowerShell 7.6.5에서 dry-run 정상 완료.
# Windows PowerShell powershell.exe에서는 시스템 실행 정책이 본문 실행 전에 차단했음.
# 실행 정책을 변경하거나 우회하지 마세요.
$ErrorActionPreference = 'Stop'
$TempRoot = 'C:\Users\MING\AppData\Local\Temp'

$Candidates = @(
    # 근거: pytest 격리 실행 산출물; 파일 5개와 하위 디렉터리 8개.
    [pscustomobject]@{
        Path = 'C:\Users\MING\AppData\Local\Temp\pytest-codex-stock-monitor-0712dfd8eaa84b68b9b88cf0c940cb39'
        Reason = 'pytest 격리 실행 산출물; 고유 경로의 소스 참조 없음'
    },
    # 근거: pytest 격리 실행 산출물; 파일 1개와 하위 디렉터리 2개.
    [pscustomobject]@{
        Path = 'C:\Users\MING\AppData\Local\Temp\pytest-codex-stock-monitor-6aed5d02457e4bd5b6a6b23afaf60d3e'
        Reason = 'pytest 격리 실행 산출물; 고유 경로의 소스 참조 없음'
    },
    # 근거: pytest 격리 실행 산출물; 파일 55개와 하위 디렉터리 104개.
    [pscustomobject]@{
        Path = 'C:\Users\MING\AppData\Local\Temp\pytest-codex-stock-monitor-655a03a29eaf4690848fde0c639f44c9'
        Reason = 'pytest 격리 실행 산출물; 고유 경로의 소스 참조 없음'
    },
    # 근거: pytest 격리 실행 산출물; 파일 11개와 하위 디렉터리 18개.
    [pscustomobject]@{
        Path = 'C:\Users\MING\AppData\Local\Temp\pytest-codex-stock-monitor-64757b1b7df34ea89cbb2401d86296dd'
        Reason = 'pytest 격리 실행 산출물; 고유 경로의 소스 참조 없음'
    },
    # 근거: pytest 격리 실행 산출물; 파일 1개와 하위 디렉터리 2개.
    [pscustomobject]@{
        Path = 'C:\Users\MING\AppData\Local\Temp\pytest-codex-stock-monitor-659286aa98564ff0b4b3e8fed36c801d'
        Reason = 'pytest 격리 실행 산출물; 고유 경로의 소스 참조 없음'
    },
    # 근거: pytest 격리 실행 산출물; 파일 12개와 하위 디렉터리 20개.
    [pscustomobject]@{
        Path = 'C:\Users\MING\AppData\Local\Temp\pytest-codex-stock-monitor-01894eddd1a2464390fc7b07cfb47534'
        Reason = 'pytest 격리 실행 산출물; 고유 경로의 소스 참조 없음'
    }
)

function Test-TreeExclusiveRead {
    param([Parameter(Mandatory)][string]$Path)

    try {
        $files = @(Get-ChildItem -LiteralPath $Path -Force -File -Recurse -ErrorAction Stop)
    }
    catch {
        return [pscustomobject]@{ Passed = $false; Detail = '파일 목록 확인 실패' }
    }

    foreach ($file in $files) {
        $stream = $null
        try {
            $stream = [System.IO.File]::Open(
                $file.FullName,
                [System.IO.FileMode]::Open,
                [System.IO.FileAccess]::Read,
                [System.IO.FileShare]::None
            )
        }
        catch {
            return [pscustomobject]@{
                Passed = $false
                Detail = "열기 실패 또는 사용 중: $($file.Name)"
            }
        }
        finally {
            if ($null -ne $stream) { $stream.Dispose() }
        }
    }

    return [pscustomobject]@{ Passed = $true; Detail = '독점 읽기 확인 통과' }
}

$processScanPassed = $false
$processes = @()
try {
    $processes = @(Get-CimInstance Win32_Process -ErrorAction Stop)
    $processScanPassed = ($processes.Count -gt 0)
}
catch {
    $processScanPassed = $false
}

$VerifiedCandidates = [System.Collections.Generic.List[string]]::new()

foreach ($candidate in $Candidates) {
    $path = $candidate.Path

    if (-not (Test-Path -LiteralPath $path -PathType Container)) {
        Write-Output "없음: $path"
        continue
    }

    $resolved = (Resolve-Path -LiteralPath $path).Path
    $leaf = [System.IO.Path]::GetFileName($resolved.TrimEnd('\'))
    $parent = [System.IO.Path]::GetDirectoryName($resolved.TrimEnd('\'))
    $item = Get-Item -LiteralPath $resolved -Force

    # 지정된 임시 루트의 직접 하위 pytest 폴더만 허용합니다.
    if ($parent -ine $TempRoot -or $leaf -notmatch '^pytest-codex-stock-monitor-[0-9a-f]{32}$') {
        Write-Output "검토: 허용 경로 범위를 벗어남: $resolved"
        continue
    }

    if (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
        Write-Output "검토: 링크/재분석 지점: $resolved"
        continue
    }

    if (-not $processScanPassed) {
        Write-Output "검토: 프로세스 확인 실패: $resolved"
        continue
    }

    $processMatches = @(
        $processes | Where-Object {
            $_.ProcessId -ne $PID -and
            -not [string]::IsNullOrWhiteSpace([string]$_.CommandLine) -and
            ([string]$_.CommandLine).IndexOf(
                $resolved,
                [System.StringComparison]::OrdinalIgnoreCase
            ) -ge 0
        }
    )

    if ($processMatches.Count -gt 0) {
        Write-Output "검토: 프로세스 명령행에서 경로 발견: $resolved"
        continue
    }

    $lockCheck = Test-TreeExclusiveRead -Path $resolved
    if (-not $lockCheck.Passed) {
        Write-Output "검토: $($lockCheck.Detail): $resolved"
        continue
    }

    $VerifiedCandidates.Add($resolved)
    Write-Output "DRY-RUN: $resolved"
    Write-Output "  근거: $($candidate.Reason)"
    Write-Output "  확인: $($lockCheck.Detail)"
}

# 실제 삭제를 선택할 경우에만 아래 블록 전체를 사람이 직접 주석 해제합니다.
# 삭제 전 이 스크립트를 다시 실행하고 DRY-RUN 경로를 재확인하세요.
# foreach ($path in $VerifiedCandidates) {
#     if (Test-Path -LiteralPath $path -PathType Container) {
#         Remove-Item -LiteralPath $path -Recurse -Force
#     }
# }
