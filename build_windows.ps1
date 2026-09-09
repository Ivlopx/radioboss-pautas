$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv")) {
    py -3 -m venv .venv
}

& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller
& .\.venv\Scripts\pyinstaller.exe `
    --noconfirm `
    --clean `
    --windowed `
    --name GeneradorPautaRadio `
    --collect-all openpyxl `
    app.py

Write-Host "Aplicación creada en dist\GeneradorPautaRadio\GeneradorPautaRadio.exe"

