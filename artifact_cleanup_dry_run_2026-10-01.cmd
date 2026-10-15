@echo off
setlocal EnableExtensions DisableDelayedExpansion
title Stock Monitor artifact review and optional cleanup
set "EXIT_CODE=0"

echo Stock Monitor temporary artifact review
echo Each target is listed first. Deletion needs Y and the exact word DELETE.
echo This CMD does not start PowerShell. The window pauses at the end.
echo Process and open-handle status cannot be checked by this CMD file.
echo.

:target1
set "TARGET=C:\Users\MING\AppData\Local\Temp\pytest-codex-stock-monitor-0712dfd8eaa84b68b9b88cf0c940cb39"
if not exist "%TARGET%\." (
    echo MISSING: "%TARGET%"
    goto :target2
)
echo ============================================================
echo TARGET: "%TARGET%"
echo Reason: isolated pytest output; 5 files and 8 subdirectories.
dir /a /s "%TARGET%"
if errorlevel 1 (
    echo REVIEW: listing failed; keeping this target.
    set "EXIT_CODE=1"
    goto :target2
)
choice /c YN /n /m "Delete this exact directory? Y=continue, N=keep: "
if errorlevel 2 (
    echo Kept: "%TARGET%"
    goto :target2
)
set "CONFIRM="
set /p "CONFIRM=Type DELETE exactly to remove it, or anything else to keep it: "
if /i not "%CONFIRM%"=="DELETE" (
    echo Confirmation did not match. Kept: "%TARGET%"
    goto :target2
)
if not exist "%TARGET%\." (
    echo REVIEW: target disappeared before deletion; skipped.
    goto :target2
)
rmdir /s /q "%TARGET%"
if errorlevel 1 (
    echo ERROR: deletion failed: "%TARGET%"
    set "EXIT_CODE=1"
    goto :target2
)
if exist "%TARGET%\." (
    echo ERROR: target remains after deletion attempt: "%TARGET%"
    set "EXIT_CODE=1"
) else echo Deleted: "%TARGET%"
goto :target2

:target2
set "TARGET=C:\Users\MING\AppData\Local\Temp\pytest-codex-stock-monitor-6aed5d02457e4bd5b6a6b23afaf60d3e"
if not exist "%TARGET%\." (
    echo MISSING: "%TARGET%"
    goto :target3
)
echo ============================================================
echo TARGET: "%TARGET%"
echo Reason: isolated pytest output; 1 file and 2 subdirectories.
dir /a /s "%TARGET%"
if errorlevel 1 (
    echo REVIEW: listing failed; keeping this target.
    set "EXIT_CODE=1"
    goto :target3
)
choice /c YN /n /m "Delete this exact directory? Y=continue, N=keep: "
if errorlevel 2 (
    echo Kept: "%TARGET%"
    goto :target3
)
set "CONFIRM="
set /p "CONFIRM=Type DELETE exactly to remove it, or anything else to keep it: "
if /i not "%CONFIRM%"=="DELETE" (
    echo Confirmation did not match. Kept: "%TARGET%"
    goto :target3
)
if not exist "%TARGET%\." (
    echo REVIEW: target disappeared before deletion; skipped.
    goto :target3
)
rmdir /s /q "%TARGET%"
if errorlevel 1 (
    echo ERROR: deletion failed: "%TARGET%"
    set "EXIT_CODE=1"
    goto :target3
)
if exist "%TARGET%\." (
    echo ERROR: target remains after deletion attempt: "%TARGET%"
    set "EXIT_CODE=1"
) else echo Deleted: "%TARGET%"
goto :target3

:target3
set "TARGET=C:\Users\MING\AppData\Local\Temp\pytest-codex-stock-monitor-655a03a29eaf4690848fde0c639f44c9"
if not exist "%TARGET%\." (
    echo MISSING: "%TARGET%"
    goto :target4
)
echo ============================================================
echo TARGET: "%TARGET%"
echo Reason: isolated pytest output; 55 files and 104 subdirectories.
dir /a /s "%TARGET%"
if errorlevel 1 (
    echo REVIEW: listing failed; keeping this target.
    set "EXIT_CODE=1"
    goto :target4
)
choice /c YN /n /m "Delete this exact directory? Y=continue, N=keep: "
if errorlevel 2 (
    echo Kept: "%TARGET%"
    goto :target4
)
set "CONFIRM="
set /p "CONFIRM=Type DELETE exactly to remove it, or anything else to keep it: "
if /i not "%CONFIRM%"=="DELETE" (
    echo Confirmation did not match. Kept: "%TARGET%"
    goto :target4
)
if not exist "%TARGET%\." (
    echo REVIEW: target disappeared before deletion; skipped.
    goto :target4
)
rmdir /s /q "%TARGET%"
if errorlevel 1 (
    echo ERROR: deletion failed: "%TARGET%"
    set "EXIT_CODE=1"
    goto :target4
)
if exist "%TARGET%\." (
    echo ERROR: target remains after deletion attempt: "%TARGET%"
    set "EXIT_CODE=1"
) else echo Deleted: "%TARGET%"
goto :target4

:target4
set "TARGET=C:\Users\MING\AppData\Local\Temp\pytest-codex-stock-monitor-64757b1b7df34ea89cbb2401d86296dd"
if not exist "%TARGET%\." (
    echo MISSING: "%TARGET%"
    goto :target5
)
echo ============================================================
echo TARGET: "%TARGET%"
echo Reason: isolated pytest output; 11 files and 18 subdirectories.
dir /a /s "%TARGET%"
if errorlevel 1 (
    echo REVIEW: listing failed; keeping this target.
    set "EXIT_CODE=1"
    goto :target5
)
choice /c YN /n /m "Delete this exact directory? Y=continue, N=keep: "
if errorlevel 2 (
    echo Kept: "%TARGET%"
    goto :target5
)
set "CONFIRM="
set /p "CONFIRM=Type DELETE exactly to remove it, or anything else to keep it: "
if /i not "%CONFIRM%"=="DELETE" (
    echo Confirmation did not match. Kept: "%TARGET%"
    goto :target5
)
if not exist "%TARGET%\." (
    echo REVIEW: target disappeared before deletion; skipped.
    goto :target5
)
rmdir /s /q "%TARGET%"
if errorlevel 1 (
    echo ERROR: deletion failed: "%TARGET%"
    set "EXIT_CODE=1"
    goto :target5
)
if exist "%TARGET%\." (
    echo ERROR: target remains after deletion attempt: "%TARGET%"
    set "EXIT_CODE=1"
) else echo Deleted: "%TARGET%"
goto :target5

:target5
set "TARGET=C:\Users\MING\AppData\Local\Temp\pytest-codex-stock-monitor-659286aa98564ff0b4b3e8fed36c801d"
if not exist "%TARGET%\." (
    echo MISSING: "%TARGET%"
    goto :target6
)
echo ============================================================
echo TARGET: "%TARGET%"
echo Reason: isolated pytest output; 1 file and 2 subdirectories.
dir /a /s "%TARGET%"
if errorlevel 1 (
    echo REVIEW: listing failed; keeping this target.
    set "EXIT_CODE=1"
    goto :target6
)
choice /c YN /n /m "Delete this exact directory? Y=continue, N=keep: "
if errorlevel 2 (
    echo Kept: "%TARGET%"
    goto :target6
)
set "CONFIRM="
set /p "CONFIRM=Type DELETE exactly to remove it, or anything else to keep it: "
if /i not "%CONFIRM%"=="DELETE" (
    echo Confirmation did not match. Kept: "%TARGET%"
    goto :target6
)
if not exist "%TARGET%\." (
    echo REVIEW: target disappeared before deletion; skipped.
    goto :target6
)
rmdir /s /q "%TARGET%"
if errorlevel 1 (
    echo ERROR: deletion failed: "%TARGET%"
    set "EXIT_CODE=1"
    goto :target6
)
if exist "%TARGET%\." (
    echo ERROR: target remains after deletion attempt: "%TARGET%"
    set "EXIT_CODE=1"
) else echo Deleted: "%TARGET%"
goto :target6

:target6
set "TARGET=C:\Users\MING\AppData\Local\Temp\pytest-codex-stock-monitor-01894eddd1a2464390fc7b07cfb47534"
if not exist "%TARGET%\." (
    echo MISSING: "%TARGET%"
    goto :finish
)
echo ============================================================
echo TARGET: "%TARGET%"
echo Reason: isolated pytest output; 12 files and 20 subdirectories.
dir /a /s "%TARGET%"
if errorlevel 1 (
    echo REVIEW: listing failed; keeping this target.
    set "EXIT_CODE=1"
    goto :finish
)
choice /c YN /n /m "Delete this exact directory? Y=continue, N=keep: "
if errorlevel 2 (
    echo Kept: "%TARGET%"
    goto :finish
)
set "CONFIRM="
set /p "CONFIRM=Type DELETE exactly to remove it, or anything else to keep it: "
if /i not "%CONFIRM%"=="DELETE" (
    echo Confirmation did not match. Kept: "%TARGET%"
    goto :finish
)
if not exist "%TARGET%\." (
    echo REVIEW: target disappeared before deletion; skipped.
    goto :finish
)
rmdir /s /q "%TARGET%"
if errorlevel 1 (
    echo ERROR: deletion failed: "%TARGET%"
    set "EXIT_CODE=1"
    goto :finish
)
if exist "%TARGET%\." (
    echo ERROR: target remains after deletion attempt: "%TARGET%"
    set "EXIT_CODE=1"
) else echo Deleted: "%TARGET%"

:finish
echo.
if not "%EXIT_CODE%"=="0" echo An operation reported an error; review the messages above.
echo Finished. Press any key to close this window.
pause >nul
exit /b %EXIT_CODE%
