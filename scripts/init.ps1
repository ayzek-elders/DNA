# Function to load environment variables from .env file
function Import-DotEnv {
  param (
    [string]$EnvPath = "../.env"
  )
  try {
    $envContent = Get-Content $EnvPath -ErrorAction Stop
    foreach ($line in $envContent) {
      if ($line -match '^([^=]+)=(.*)$') {
        Set-Item -Path "Env:$($matches[1])" -Value $matches[2]
      }
    }
    Write-Host "Environment variables loaded successfully" -ForegroundColor Green
  }
  catch {
    Write-Host "Error loading .env file: $_" -ForegroundColor Red
    exit 1
  }
}

# Function to setup and configure PostgreSQL
function Initialize-PostgreSQL {
  try {
    Write-Host "Setting up Docker compose" -ForegroundColor Green
    docker-compose -f ../docker-compose.yml up -d

    # Create database and user
    $commands = @(
      "CREATE DATABASE $POSTGRES_DB;",
      "CREATE USER $POSTGRES_USER WITH PASSWORD '$POSTGRES_PASSWORD';",
      "GRANT ALL PRIVILEGES ON DATABASE $POSTGRES_DB TO $POSTGRES_USER;"
    )

    foreach ($cmd in $commands) {
      docker exec -it postgres psql -U postgres -d postgres -c $cmd
    }

    # Wait for PostgreSQL container to be ready
    if ([string]::IsNullOrEmpty($env:POSTGRES_CONTAINER_NAME)) {
      throw "POSTGRES_CONTAINER_NAME environment variable is not set"
    }

    Write-Host "Waiting for PostgreSQL container to be ready..." -ForegroundColor Yellow
    while (-not (docker ps -f "name=$env:POSTGRES_CONTAINER_NAME" -f "status=running" --format "{{.Names}}" | Select-String -Pattern "$env:POSTGRES_CONTAINER_NAME")) {
      Start-Sleep -Seconds 1
    }
    Write-Host "PostgreSQL container is ready" -ForegroundColor Green
  }
  catch {
    Write-Host "Error setting up PostgreSQL: $_" -ForegroundColor Red
    exit 1
  }
}

# Function to setup Python virtual environment
function Initialize-VirtualEnvironment {
  try {
    Set-Location ../backend
    $venvPath = ".venv/"
        
    if (-not (Test-Path -Path $venvPath)) {
      Write-Host "Creating new virtual environment" -ForegroundColor Yellow
      pip install uv
      pip install virtualenv
      if (-not $?) { throw "Failed to install uv" }
      python -m venv .venv
      if (-not $?) { throw "Failed to create virtual environment" }
      python -m uv sync
      if (-not $?) { throw "Failed to sync dependencies" }
            
      Write-Host "Dependencies installed successfully" -ForegroundColor Green
    }
    else {
      Write-Host "Virtual environment already exists" -ForegroundColor Green
    }

    # Activate virtual environment and apply migrations
    if (Test-Path -Path $venvPath) {
      Write-Host "Activating virtual environment" -ForegroundColor Blue
      & .\.venv\Scripts\Activate.ps1
            
      Write-Host "Applying database migrations" -ForegroundColor Yellow
      alembic upgrade head
      if (-not $?) { throw "Failed to apply migrations" }
            
      Write-Host "Migrations applied successfully" -ForegroundColor Green
    }
  }
  catch {
    Write-Host "Error setting up virtual environment: $_" -ForegroundColor Red
    exit 1
  }
}

# Main execution
try {
  Write-Host "Starting initialization process..." -ForegroundColor Cyan
    
  Import-DotEnv
  Initialize-PostgreSQL
  Initialize-VirtualEnvironment
    
  Write-Host "Initialization completed successfully!" -ForegroundColor Green
}
catch {
  Write-Host "Fatal error during initialization: $_" -ForegroundColor Red
  exit 1
}