$ErrorActionPreference = "Stop"

function Ensure-Db($Name) {
    $user = if ($env:DB__USER) { $env:DB__USER } else { "default" }
    $exists = docker compose exec -T db psql -U $user -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$Name'"
    if (("$exists").Trim() -ne "1") {
        docker compose exec -T db createdb -U $user $Name
    }
}

function Count-Matches($Text, $Pattern) {
    $match = [regex]::Match($Text, $Pattern)
    if ($match.Success) { return [int]$match.Groups[1].Value }
    return 0
}

function Run-Capture($Name, $Command) {
    Write-Host ""
    Write-Host "== $Name =="
    $output = & powershell -NoProfile -ExecutionPolicy Bypass -Command $Command 2>&1
    $text = ($output | Out-String)
    Write-Host $text
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
    return $text
}

docker compose up -d db redis
Ensure-Db "crv_workforce_test"
Ensure-Db "crv_workforce_migcheck"

$dbUser = if ($env:DB__USER) { $env:DB__USER } else { "default" }
$dbPassword = if ($env:DB__PASSWORD) { $env:DB__PASSWORD } else { "password" }
$redisPassword = if ($env:REDIS__PASSWORD) { $env:REDIS__PASSWORD } else { "password" }

$env:APP__ENV = "development"
$env:DB__HOST = "localhost"
$env:DB__PORT = "5432"
$env:DB__USER = $dbUser
$env:DB__PASSWORD = $dbPassword
$env:REDIS__HOST = "localhost"
$env:REDIS__PASSWORD = $redisPassword
$env:CRV_REQUIRE_POSTGRES = "1"
$env:TEST_DATABASE_URL = "postgresql+asyncpg://$dbUser`:$dbPassword@localhost:5432/crv_workforce_test"

$pytest = Run-Capture "pytest" "python -m pytest -q"
$pytestPassed = Count-Matches $pytest "(\d+) passed"
$pytestSkipped = Count-Matches $pytest "(\d+) skipped"
if ($pytestSkipped -ne 0) {
    throw "PostgreSQL-required pytest run must have 0 skipped tests, got $pytestSkipped"
}

$env:DB__NAME = "crv_workforce_migcheck"
$migration = Run-Capture "alembic migration check" "alembic upgrade head; alembic downgrade 0002; alembic upgrade head; alembic check"

Push-Location webapp
$devProcess = $null
try {
    $npmTest = Run-Capture "npm test" "npm test"
    $npmBuild = Run-Capture "npm run build" "npm run build"
    $env:VITE_MOCK = "1"
    $env:CRV_MOCK_URL = "http://127.0.0.1:4175"
    $devCommand = "Set-Location '$((Get-Location).Path)'; `$env:VITE_MOCK='1'; npm run dev -- --host 127.0.0.1 --port 4175"
    $devProcess = Start-Process -FilePath "powershell" -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $devCommand -PassThru -WindowStyle Hidden
    for ($i = 0; $i -lt 30; $i++) {
        try {
            Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:4175" | Out-Null
            break
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
    $overflow = Run-Capture "npm run test:overflow" "npm run test:overflow"
} finally {
    if ($devProcess -and -not $devProcess.HasExited) {
        Stop-Process -Id $devProcess.Id -Force
    }
    Pop-Location
}

Write-Host ""
Write-Host "| Group | Passed | Skipped | Status |"
Write-Host "|---|---:|---:|---|"
Write-Host "| pytest | $pytestPassed | $pytestSkipped | OK |"
Write-Host "| alembic | n/a | n/a | OK |"
Write-Host "| npm test | n/a | n/a | OK |"
Write-Host "| npm build | n/a | n/a | OK |"
Write-Host "| overflow 360/390/430 | n/a | n/a | OK |"
