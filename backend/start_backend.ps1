$ErrorActionPreference = "Stop"

$env:PYTHONDONTWRITEBYTECODE = "1"

.\.venv\Scripts\python.exe -B -m uvicorn app.main:app `
  --host 127.0.0.1 `
  --port 8001 `
  --reload `
  --reload-dir app
