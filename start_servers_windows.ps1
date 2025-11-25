# Start Servers on Windows

Write-Host "Starting Backend..."
Start-Process -FilePath "python" -ArgumentList "main.py" -WorkingDirectory "web/backend/api_gateway" -WindowStyle Minimized

Write-Host "Starting Frontend..."
Start-Process -FilePath "cmd" -ArgumentList "/c npm run dev" -WorkingDirectory "web/frontend" -WindowStyle Minimized

Write-Host "Servers started in background windows."
