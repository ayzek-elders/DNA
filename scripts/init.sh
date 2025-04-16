#!/bin/bash

# Set error handling
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to load environment variables from .env file
load_env() {
    local env_path="../.env"
    echo -e "${BLUE}Loading environment variables...${NC}"
    
    if [ ! -f "$env_path" ]; then
        echo -e "${RED}Error: .env file not found at $env_path${NC}"
        exit 1
    fi

    while IFS= read -r line; do
        # Skip comments and empty lines
        if [[ $line =~ ^[[:space:]]*# ]] || [[ -z $line ]]; then
            continue
        fi
        
        # Extract key and value
        if [[ $line =~ ^[[:space:]]*([^[:space:]]+)[[:space:]]*=[[:space:]]*(.*)$ ]]; then
            key="${BASH_REMATCH[1]}"
            value="${BASH_REMATCH[2]}"
            echo -e "${CYAN}Setting environment variable: $key=${value}${NC}"
            export "$key=$value"
        fi
    done < "$env_path"
    
    echo -e "${GREEN}Environment variables loaded successfully${NC}"
}

# Function to setup and configure PostgreSQL
initialize_postgresql() {
    echo -e "${GREEN}Setting up Docker compose${NC}"
    docker-compose -f ../docker-compose.yml up -d

    echo -e "${YELLOW}Waiting for PostgreSQL container to be ready...${NC}"
    if [ -z "$POSTGRES_CONTAINER_NAME" ]; then
        echo -e "${RED}Error: POSTGRES_CONTAINER_NAME environment variable is not set${NC}"
        exit 1
    fi

    # Wait for PostgreSQL to be ready
    while ! docker ps -f "name=$POSTGRES_CONTAINER_NAME" -f "status=running" --format "{{.Names}}" | grep -q "$POSTGRES_CONTAINER_NAME"; do
        sleep 1
    done
    echo -e "${GREEN}PostgreSQL container is ready${NC}"

    # Create database and user
    commands=(
        "CREATE DATABASE $POSTGRES_DB;"
        "CREATE USER $POSTGRES_USER WITH PASSWORD '$POSTGRES_PASSWORD';"
        "GRANT ALL PRIVILEGES ON DATABASE $POSTGRES_DB TO $POSTGRES_USER;"
    )

    for cmd in "${commands[@]}"; do
        docker exec -it postgres psql -U postgres -d postgres -c "$cmd"
    done
}

# Function to setup Python virtual environment
initialize_virtual_environment() {
    cd ../backend || exit 1
    VENV_PATH=".venv/"

    if [ ! -d "$VENV_PATH" ]; then
        echo -e "${YELLOW}Creating new virtual environment${NC}"
        pip install uv || {
            echo -e "${RED}Failed to install uv${NC}"
            exit 1
        }

        uv sync || {
            echo -e "${RED}Failed to sync dependencies${NC}"
            exit 1
        }

        echo -e "${GREEN}Dependencies installed successfully${NC}"
    else
        echo -e "${GREEN}Virtual environment already exists${NC}"
    fi

    # Activate virtual environment and apply migrations
    if [ -d "$VENV_PATH" ]; then
        echo -e "${BLUE}Activating virtual environment${NC}"
        source .venv/bin/activate

        echo -e "${YELLOW}Applying database migrations${NC}"
        alembic upgrade head || {
            echo -e "${RED}Failed to apply migrations${NC}"
            exit 1
        }

        echo -e "${GREEN}Migrations applied successfully${NC}"
    fi
}

# Main execution
main() {
    echo -e "${CYAN}Starting initialization process...${NC}"

    load_env
    initialize_postgresql
    initialize_virtual_environment

    echo -e "${GREEN}Initialization completed successfully!${NC}"
}

# Execute main function
main
