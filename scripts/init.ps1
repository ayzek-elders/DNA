Get-Content -LiteralPath ../.local.env | ForEach-Object {
  $line = $_.trim()
  if ($line -match "^\s*#") {
    Write-Verbose -Message "Found comment $line at line $linecursor. discarding"
  }
  elseif ($line -match "^\s*$") {
    Write-Verbose -Message "Found a blank line at line $linecursor, discarding"
  }
  elseif ($line -match "^\s*(?<key>[^\n\b\a\f\v\r\s]+)\s*=\s*(?<value>[^\n\b\a\f\v\r]*)$") {
    $key = $Matches["key"]
    $value = $Matches["value"]
    Write-Verbose -Message "Found [$key] with value [$value]"
    [System.Environment]::SetEnvironmentVariable($key, $value, [System.EnvironmentVariableTarget]::Process)
  
  }
}

docker-compose -f ../docker-compose.yml up -d

docker exec -it postgres psql -U postgres -d postgres -c "CREATE DATABASE $POSTGRES_DB;"

docker exec -it postgres psql -U postgres -d postgres -c "CREATE USER $POSTGRES_USER WITH PASSWORD '$POSTGRES_PASSWORD';"

docker exec -it postgres psql -U postgres -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE $POSTGRES_DB TO $POSTGRES_USER;"


