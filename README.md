# Project Setup Guide

## Prerequisites

- Docker and Docker Compose installed
- Git (for cloning the repository)
- PostgreSQL client (optional, for direct database access)
- if using macos curl -LsSf https://astral.sh/uv/install.sh | sh for windows powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

## Initial Setup

1. Clone the repository
2. Create a `.env` file in the root directory with the following variables:
   ```env
   POSTGRES_DB=your_database_name
   POSTGRES_USER=your_username
   POSTGRES_PASSWORD=your_secure_password
   ```

## Starting the Project

### For Windows Users

1. Open PowerShell in the project directory
2. Navigate to the scripts directory:
   ```powershell
   cd scripts
   ```
3. Run the initialization script:
   ```powershell
   .\init.ps1
   ```

### For macOS/Linux Users

1. Open Terminal in the project directory
2. Navigate to the scripts directory:
   ```bash
   cd scripts
   ```
3. Make the initialization script executable:
   ```bash
   chmod +x init.sh
   ```
4. Run the initialization script:
   ```bash
   ./init.sh
   ```
