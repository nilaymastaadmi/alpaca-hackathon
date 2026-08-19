Get-Content .env | ForEach-Object {
    if ($_ -match '^\s*([^=]+)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
    }
}
curl.exe -s https://paper-api.alpaca.markets/v2/account `
    -H "APCA-API-KEY-ID: $env:ALPACA_API_KEY" `
    -H "APCA-API-SECRET-KEY: $env:ALPACA_SECRET_KEY"
