#!/bin/bash

# Read and set environment variables from .local.env
while IFS= read -r line; do
  # Skip comments and empty lines
  if [[ $line =~ ^[[:space:]]*# ]] || [[ -z $line ]]; then
    continue
  fi
  
  # Extract key and value
  if [[ $line =~ ^[[:space:]]*([^[:space:]]+)[[:space:]]*=[[:space:]]*(.*)$ ]]; then
    key="${BASH_REMATCH[1]}"
    value="${BASH_REMATCH[2]}"
    export "$key=$value"
  fi
done < ../.local.env

# Start Docker containers
docker-compose -f ../docker-compose.yml up -d

# Create database and user
docker exec -it postgres psql -U postgres -d postgres -c "CREATE DATABASE $POSTGRES_DB;"
docker exec -it postgres psql -U postgres -d postgres -c "CREATE USER $POSTGRES_USER WITH PASSWORD '$POSTGRES_PASSWORD';"
docker exec -it postgres psql -U postgres -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE $POSTGRES_DB TO $POSTGRES_USER;"
