# Stop on first error
$ErrorActionPreference = "Stop"

# Navigate to project root (script → parent → root)
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$ROOT_DIR = Resolve-Path "$SCRIPT_DIR\.."
Set-Location $ROOT_DIR

Write-Host "[RUN] Starting all 5 nodes in background"

$P1 = Start-Process -FilePath "powershell" -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File .\run\run_p1.ps1" -PassThru
$P2 = Start-Process -FilePath "powershell" -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File .\run\run_p2.ps1" -PassThru
$P3 = Start-Process -FilePath "powershell" -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File .\run\run_p3.ps1" -PassThru
$P4 = Start-Process -FilePath "powershell" -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File .\run\run_p4.ps1" -PassThru
$P5 = Start-Process -FilePath "powershell" -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File .\run\run_p5.ps1" -PassThru

$PID1 = $P1.Id
$PID2 = $P2.Id
$PID3 = $P3.Id
$PID4 = $P4.Id
$PID5 = $P5.Id

Write-Host "[RUN] Nodes PIDs: $PID1 $PID2 $PID3 $PID4 $PID5"
Write-Host "[RUN] Use .\run\kill_all.ps1 to stop them."

# Wait for all processes to exit
Wait-Process -Id $PID1, $PID2, $PID3, $PID4, $PID5
