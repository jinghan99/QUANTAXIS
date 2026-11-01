param(
    [ValidateSet('start','stop','restart','status','logs','jupyter')][string]$Action = 'status',
    [ValidateSet('dev','prod','all')][string]$Environment = 'dev'
)
$ErrorActionPreference = 'Stop'
$profiles = if ($Environment -eq 'all') { @('dev','prod') } else { @($Environment) }
$services = @($profiles | ForEach-Object { "quantaxis-$_-backend"; "quantaxis-$_-frontend"; if ($_ -eq 'dev') { 'quantaxis-dev-jupyter' } })
switch ($Action) {
    'start' { wsl -d Ubuntu-24.04 -- systemctl --user start @services }
    'restart' { wsl -d Ubuntu-24.04 -- systemctl --user restart @services }
    'stop' { wsl -d Ubuntu-24.04 -- systemctl --user stop @services }
    'status' { wsl -d Ubuntu-24.04 -- systemctl --user --no-pager status @services }
    'logs' { foreach ($profile in $profiles) { wsl -d Ubuntu-24.04 -- tail -n 50 "/home/jinghan/.local/share/quantaxis-local/$profile/logs/backend.service.log" "/home/jinghan/.local/share/quantaxis-local/$profile/logs/frontend.service.log" } }
    'jupyter' { wsl -d Ubuntu-24.04 -- cat /home/jinghan/.local/share/quantaxis-local/jupyter-url.txt }
}
if ($LASTEXITCODE -ne 0) { throw "WSL command failed: $LASTEXITCODE" }
