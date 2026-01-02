# Clear Conversation History

**Using curl (Windows/PowerShell):**
```powershell
curl.exe -X DELETE http://127.0.0.1:8000/api/sessions
```

**Using Native PowerShell:**
```powershell
Invoke-RestMethod -Method Delete -Uri http://127.0.0.1:8000/api/sessions
```

# Get Feedback Data
curl http://localhost:8000/api/analytics/feedback