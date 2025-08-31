# Food Label Scanner v0.1.0

A web application that scans food labels and extracts ingredients using OCR technology. It identifies potentially concerning ingredients by checking against a predefined NoGo list.

## Features

- Mobile-friendly camera interface with image cropping
- OCR-powered ingredient extraction 
- NoGo ingredients identification
- User authentication and dashboard
- Scan history with comments
- User profile management
- Azure cloud integration (Form Recognizer, Blob Storage, SQL Database)
- AI-powered ingredient explanations
- Responsive design for all devices

## Technologies Used

- Flask (Backend)
- HTML/CSS/JavaScript (Frontend)
- Azure Form Recognizer (Text Recognition)
- Azure Blob Storage (Image Storage)
- Cropper.js (Image Cropping)
- Azure SQL Server (Database)
- Claude AI (Image validation and explanations)

## Local Installation

1. Clone the repository:

```bash
git clone https://github.com/developer2maingowholefood-cpu/food-label-scanner.git
cd food-label-scanner
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configuration:
   Copy `src/config.example.json` to `src/config.json` and update with your Azure Form Recognizer credentials.

4. Run the application:

```bash
# Using Docker (Recommended)
./run_local.sh

# Or using Flask CLI
source venv_food_app/bin/activate
export FLASK_APP=src/app.py
export PYTHONPATH=src
flask run --host=0.0.0.0 --port=8000
```

## Environment Variables

Configure your environment variables in `azure-production.env`:

```bash
# Azure SQL Database
DATABASE_URL=mssql+pyodbc://username:password@server.database.windows.net:1433/database?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no

# Azure Form Recognizer
AZURE_FORM_RECOGNIZER_ENDPOINT=your-form-recognizer-endpoint
AZURE_FORM_RECOGNIZER_KEY=your-form-recognizer-key

# Azure Blob Storage
AZURE_STORAGE_ACCOUNT_NAME=your-account-name
AZURE_STORAGE_ACCOUNT_KEY=your-account-key
AZURE_STORAGE_CONTAINER_NAME=food-scanner-images

# Claude AI
CLAUDE_SONNET_API_KEY=your-claude-api-key

# Email (Brevo)
BREVO_API_KEY=your-brevo-api-key
MAIL_DEFAULT_SENDER=your-email@example.com

# Flask Configuration
SECRET_KEY=your-production-secret-key
```

## License

This project is licensed under the MIT License.