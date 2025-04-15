$envContent = Get-Content ../.local.env
foreach ($line in $envContent) {
  if ($line -match '^([^=]+)=(.*)$') {
    Set-Item -Path "Env:$($matches[1])" -Value $matches[2]
  }
}


docker-compose -f ../docker-compose.yml up -d

docker exec -it postgres psql -U postgres -d postgres -c "CREATE DATABASE $POSTGRES_DB;"

docker exec -it postgres psql -U postgres -d postgres -c "CREATE USER $POSTGRES_USER WITH PASSWORD '$POSTGRES_PASSWORD';"

docker exec -it postgres psql -U postgres -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE $POSTGRES_DB TO $POSTGRES_USER;"


