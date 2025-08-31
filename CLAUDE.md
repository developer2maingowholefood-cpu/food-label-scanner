# Food Label Scanner - Claude Code Configuration

## Project Overview
A Flask web application that scans food labels using OCR technology and identifies concerning ingredients against a NoGo list. Features include user authentication, image storage (local/Azure Blob), and a modern responsive dashboard.

## Technology Stack
- **Backend**: Flask 3.0.3, SQLAlchemy 2.0.40
- **Database**: Azure SQL Database (production), SQLite (local development)
- **OCR**: Azure Form Recognizer
- **Storage**: Azure Blob Storage (production), local storage (development)
- **Frontend**: HTML/CSS/JavaScript, Cropper.js
- **Authentication**: Flask-Login
- **Email**: Brevo API for password reset

## Development Commands

### Running the Application
```bash
# Recommended: Docker with fresh builds
./run_local.sh

# Alternative: Flask CLI
source venv_food_app/bin/activate
export FLASK_APP=src/app.py
export PYTHONPATH=src
flask run --host=0.0.0.0 --port=8000

# Alternative: Python directly
source venv_food_app/bin/activate
python3.11 src/app.py
```

### Testing
```bash
# Test Azure database connection
python test_azure_connection.py

# Test user functionality
python test_user_storage.py

# Basic app test
python src/test_app.py
```

### Database Operations
```bash
# Database migrations
flask db init
flask db migrate -m "description"
flask db upgrade

# Create Azure tables
python create_azure_tables.py

# Query scans
python query_scans.py
```

### Ingredients List Management
```bash
# Generate new NoGo ingredients list
cd data/ingredients/source
python generate_nogo_list.py
```

## Key Files & Directories

### Core Application
- `src/app.py` - Main Flask application
- `src/models.py` - Database models
- `src/nogo_checker.py` - Ingredient checking logic
- `src/azure_blob_service.py` - Azure Blob Storage integration

### Configuration
- `azure-production.env` - Environment variables for Azure deployment
- `src/config.json` - Azure Form Recognizer credentials (not in repo)
- `src/config.example.json` - Configuration template

### Data & Storage
- `data/ingredients/source/` - NoGo ingredients list generation
- `local_storage/images/` - Local development image storage
- `migrations/` - Database migration files

### Templates & Static Files
- `src/templates/` - HTML templates
- `src/static/` - CSS, JavaScript, favicon

## Environment Variables
Required in `azure-production.env`:
- `DATABASE_URL` - Azure SQL Database connection string
- `AZURE_FORM_RECOGNIZER_ENDPOINT` & `AZURE_FORM_RECOGNIZER_KEY` - OCR service
- `AZURE_STORAGE_ACCOUNT_NAME`, `AZURE_STORAGE_ACCOUNT_KEY`, `AZURE_STORAGE_CONTAINER_NAME` - Blob storage
- `CLAUDE_SONNET_API_KEY` - AI image validation
- `BREVO_API_KEY` & `MAIL_DEFAULT_SENDER` - Email service
- `SECRET_KEY` - Flask session security

## Code Conventions
- Python 3.11 compatibility
- Use Flask blueprints for organization
- Follow SQLAlchemy 2.0+ patterns
- Responsive design with mobile-first approach
- Error handling with user-friendly messages
- Environment-specific configurations (local vs Azure)

## Security Notes
- Never commit `config.json` or credentials
- Use environment variables for sensitive data
- SAS tokens for secure Azure Blob access
- User authentication with password reset functionality

## Git Commit Guidelines
- Use clear, descriptive commit messages that explain the "why" not just the "what"
- Follow conventional commit format: `type: description`
- Types: feat, fix, refactor, docs, test, chore
- Keep commit messages concise (1-2 sentences)
- NEVER include Claude Code attribution or co-authored-by lines in commit messages
- Example: `feat: add multiple timestamped comments system`

## Development Reminders
- ALWAYS TEST LOCALLY FIRST BEFORE PUSHING

## Troubleshooting

### Local Docker Development Issues

#### Problem: Container fails to start with "startup.sh" not found or wrong paths
**Root Cause**: The `startup.sh` script was designed for Azure deployment with complex path detection logic, but local Docker containers should use a simpler startup script.

**Solution**: Separate startup scripts and Dockerfiles for local vs Azure deployment:
- **Local Development**: Use `Dockerfile.local` with `startup-local.sh`
- **Azure Deployment**: Use `Dockerfile` with `startup-azure.sh`

**Files Created**:
- `startup-local.sh` - Simple startup script for local Docker (no path detection needed)
- `Dockerfile.local` - Minimal Dockerfile for local development (no Azure-specific dependencies)
- Updated `run_local.sh` - Uses `Dockerfile.local` for building

**Key Commands**:
```bash
# For local development
./run_local.sh

# For Azure deployment (GitHub Actions handles this)
docker build -t food-app .  # Uses main Dockerfile with startup-azure.sh
```

**Prevention**: Always keep local and Azure deployment configurations separate. Local Docker should be simple and straightforward, while Azure needs complex path detection due to Oryx build system.

### Azure Deployment Issues

#### Azure Oryx Build System Path Issues
**Problem**: Azure extracts deployment packages to `/tmp/<random-id>` but startup scripts look in `/home/site/wwwroot`
**Solution**: 
- Use custom `startup.sh` script with dynamic path detection
- Search multiple possible paths: `/tmp/*/`, `/home/site/wwwroot`
- Ensure GitHub Actions zip includes all source files properly

#### GitHub Actions Deployment Packaging
**Problem**: Source files not included in deployment package
**Solution**:
- Verify zip command includes all necessary files: `zip -r release.zip . -x exclusions`
- Ensure `package: release.zip` parameter is set in Azure deployment step
- Check that `src/` directory is included in the zip

#### Azure Blob Storage Initialization
**Problem**: Images not storing, dashboard shows "No image available"
**Symptoms**: `blob_service.initialized = false` in debug endpoint
**Root Cause**: Signal timeout mechanism interferes with Azure Blob Service initialization
**Solution**:
- Remove signal/alarm timeout from Azure Blob Service initialization
- Use simple try/catch error handling instead
- Add debug endpoint `/debug/azure-blob` to verify configuration

**Debug Steps**:
1. Check environment variables are loaded: `azure-production.env` should be loaded in Azure App Service
2. Verify Azure Storage credentials in Application Settings
3. Test blob service status with debug endpoint
4. Check container accessibility

#### Environment Variable Loading
**Problem**: Environment variables from `azure-production.env` not loaded in Azure App Service
**Solution**:
```python
# Load Azure production environment variables if in Azure App Service
is_azure_webapp = os.getenv('WEBSITE_SITE_NAME') is not None
if is_azure_webapp:
    azure_env_path = os.path.join(os.path.dirname(__file__), '..', 'azure-production.env')
    if os.path.exists(azure_env_path):
        load_dotenv(azure_env_path, override=True)
```

### Animation Implementation
**Features Added**: Image shrinking and progress ring animations
**Implementation**: CSS transitions with JavaScript DOM manipulation
- Image shrinks to 120px square after capture
- SVG progress ring with stroke-dasharray animation
- Responsive design for mobile devices

## Development Environment Setup

### Complete Dev Environment (v2.21.0)
**Location**: https://food-app-dev.azurewebsites.net/

**Key Components**:
- **Azure App Service**: `food-app-dev` (East US 2, F1 tier)
- **Azure SQL Database**: `food-app-dev-db` on server `food-app-dev-server` 
- **Azure Blob Storage**: `foodappdevstorage` with container `food-app-dev-images`
- **GitHub Actions**: Automated deployment from `dev` branch

### Critical Lessons Learned - Environment Isolation

#### Problem: Environment Variable Loading Conflict
**Issue**: Dev environment was loading `azure-production.env` file, causing it to use production Azure storage instead of dev storage.

**Root Cause**: App logic in `src/app.py` loaded production environment file for all Azure App Service deployments.

**Solution**: Modified environment loading logic to detect environment by `WEBSITE_SITE_NAME`:
```python
# Only load azure-production.env for production environment
if 'food-app-dev' not in site_name:
    # This is production environment
    load_dotenv(azure_env_path, override=True)
else:
    print("Dev environment detected - using only Azure App Service environment variables")
```

**Prevention**: Always check environment variable sources when deploying to multiple environments. Dev should be completely isolated from production configuration files.

#### Problem: Azure Dependencies Installation 
**Issue**: `ModuleNotFoundError: No module named 'azure'` during deployment.

**Root Cause**: Missing version specification for `psycopg2-binary` in requirements.txt caused Azure deployment build to fail.

**Solution**: Added explicit version: `psycopg2-binary==2.9.7`

**Prevention**: Always specify exact versions for all dependencies in requirements.txt for Azure deployments.

#### Problem: Database Table Creation
**Issue**: Dev database had no tables initially.

**Solution**: Created `create_dev_tables.py` script to initialize database schema:
- Used environment variables to target dev database specifically  
- Added SQL Server firewall rule for local IP access
- Verified table creation with proper SQLAlchemy 2.0 syntax

### Environment Configuration Scripts
- `setup-azure-dev-consistent.sh` - Creates all Azure resources with consistent naming
- `configure-dev-env-consistent.sh` - Sets all environment variables for dev environment  
- Both scripts follow naming pattern: prod (`food-app`), dev (`food-app-dev`), future UAT (`food-app-uat`)

### Naming Conventions
**Established Pattern**:
- Production: `food-app.azurewebsites.net`
- Development: `food-app-dev.azurewebsites.net` 
- Future UAT: `food-app-uat.azurewebsites.net`

**Resource Naming**: All Azure resources follow `[service]-[environment]` pattern for consistency.

## Version Information
Current version: v2.21.0 (see VERSION file)  
Change tracking: CHANGELOG.md