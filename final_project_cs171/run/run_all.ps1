# run_all.ps1
$proj = "$PSScriptRoot/.."

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$proj'; python -m src.node --id 1"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$proj'; python -m src.node --id 2"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$proj'; python -m src.node --id 3"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$proj'; python -m src.node --id 4"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$proj'; python -m src.node --id 5"
