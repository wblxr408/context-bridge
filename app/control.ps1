param([ValidateSet('status','start','stop')][string]$Action='status')
$ErrorActionPreference='Stop'
$serviceHome=Join-Path $env:USERPROFILE '.codex\services\engineering-memory'
switch ($Action) {
    'start' {
        Remove-Item -LiteralPath (Join-Path $serviceHome 'stop') -ErrorAction SilentlyContinue
        Enable-ScheduledTask -TaskName 'EngineeringMemoryListener' | Out-Null
        Start-ScheduledTask -TaskName 'EngineeringMemoryListener'
    }
    'stop' {
        New-Item -ItemType File -Path (Join-Path $serviceHome 'stop') -Force | Out-Null
        Disable-ScheduledTask -TaskName 'EngineeringMemoryListener' | Out-Null
        Write-Output 'Stop requested. An in-flight classifier is allowed to finish; automatic restart is disabled.'
    }
    'status' {
        Get-ScheduledTask -TaskName 'EngineeringMemoryListener' | Select-Object TaskName,State
        $status=Join-Path $serviceHome 'status.json'
        if (Test-Path -LiteralPath $status) { Get-Content -LiteralPath $status -Raw }
        else { Write-Output 'No heartbeat written yet.' }
    }
}
