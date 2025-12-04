Get-Process python -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -like "*python.exe" } |
    Stop-Process -Force
