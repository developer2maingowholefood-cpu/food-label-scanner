import string
import re
from flask import Flask, request, jsonify, render_template, flash, redirect, url_for, abort, send_from_directory
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient
import os
import json
import tempfile
import string  # For punctuation cleaning
from flask_cors import CORS

# Handle imports for both direct python execution and flask run
try:
    from nogo_checker import NoGoChecker
    from models import db, User, Scan, ScanComment
    from azure_blob_service import AzureBlobService
except ImportError:
    from .nogo_checker import NoGoChecker
    from .models import db, User, Scan, ScanComment
    from .azure_blob_service import AzureBlobService

import requests  # For Claude Sonnet API call
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from flask_mail import Mail, Message
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from flask_migrate import Migrate

app = Flask(__name__)
CORS(app)

# Load VERSION for display in templates
def get_version():
    """Read version from VERSION file"""
    version_file = os.path.join(os.path.dirname(__file__), '..', 'VERSION')
    try:
        with open(version_file, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return 'Unknown'

# Make VERSION available to all templates
@app.context_processor
def inject_version():
    return {'app_version': get_version()}

# Load environment variables first
load_dotenv()

# Load environment-specific variables
is_azure_webapp = os.getenv('WEBSITE_SITE_NAME') is not None
is_docker = os.path.exists('/.dockerenv')

if is_azure_webapp:
    site_name = os.getenv('WEBSITE_SITE_NAME', '')
    print(f"Detected Azure App Service: {site_name}")
    
    # Only load azure-production.env for production environment
    # Dev environment should use only Azure App Service environment variables
    if 'food-app-dev' not in site_name:
        # This is production environment
        azure_env_path = os.path.join(os.path.dirname(__file__), '..', 'azure-production.env')
        if os.path.exists(azure_env_path):
            load_dotenv(azure_env_path, override=True)
            print(f"Loaded Azure production environment from {azure_env_path}")
        else:
            print("Warning: azure-production.env not found in Azure App Service")
    else:
        print("Dev environment detected - using only Azure App Service environment variables")
elif is_docker:
    # For local Docker development, load azure-local.env
    print("Detected Docker environment")
    local_env_path = os.path.join(os.path.dirname(__file__), '..', 'azure-local.env')
    if os.path.exists(local_env_path):
        load_dotenv(local_env_path, override=True)
        print(f"Local Docker: Loaded azure-local.env for development")
    else:
        print("Warning: azure-local.env not found for local Docker development")

# App config - use SQLite for local development
# Docker detection already done above, don't redefine is_docker
database_url = os.getenv('DATABASE_URL')

if is_docker and not is_azure_webapp:
    # Force SQLite in Docker for local development (but not Azure Web Apps)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////app/instance/local.db'
    print(f"Docker detected: Using SQLite at {app.config['SQLALCHEMY_DATABASE_URI']}")
elif database_url and (is_azure_webapp or not is_docker):
    # Use Azure database for production (Azure Web Apps or non-Docker with DATABASE_URL)
    # Fix the connection string with better timeout and connection parameters
    if 'mssql+pyodbc://' in database_url:
        # Add connection timeout and pool settings for Azure SQL
        if '?' in database_url:
            app.config['SQLALCHEMY_DATABASE_URI'] = database_url + '&Connection+Timeout=30&Command+Timeout=60'
        else:
            app.config['SQLALCHEMY_DATABASE_URI'] = database_url + '?Connection+Timeout=30&Command+Timeout=60'
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url.replace('postgres://', 'postgresql://')
    print(f"Production mode: Using Azure database")
else:
    # Default to SQLite for local development outside Docker
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///food_scanner.db'
    print(f"Local development: Using SQLite at {app.config['SQLALCHEMY_DATABASE_URI']}")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')

# Session configuration - 10 minutes (safe production value)
from datetime import timedelta
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)  # Long-term persistent login
app.config['SESSION_REFRESH_EACH_REQUEST'] = False  # Don't auto-refresh, we'll handle manually

# Configure SQLAlchemy engine options for better Azure SQL performance
if 'mssql+pyodbc://' in app.config['SQLALCHEMY_DATABASE_URI']:
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'connect_args': {
            'timeout': 30,
            'login_timeout': 30
        }
    }

# Email configuration
BREVO_API_KEY = os.getenv('BREVO_API_KEY')
MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'mombini.haadi@gmail.com')

# Initialize Brevo API configuration
brevo_configuration = sib_api_v3_sdk.Configuration()
brevo_configuration.api_key['api-key'] = BREVO_API_KEY

# Initialize Brevo API instance
brevo_api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(brevo_configuration))

# Keep Flask-Mail for compatibility (but we'll use Brevo for sending)
mail = Mail(app)

# Initialize extensions
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)
db.init_app(app)
migrate = Migrate(app, db)

# Initialize global variables that will be set later
document_analysis_client = None
nogo_checker = None
blob_service = None

# Create tables with better error handling
def init_database():
    """Initialize database tables with retry logic."""
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            with app.app_context():
                db.create_all()
                print("Database tables created successfully")
                return True
        except Exception as e:
            retry_count += 1
            print(f"Database initialization attempt {retry_count} failed: {e}")
            if retry_count >= max_retries:
                print(f"Warning: Database initialization failed after {max_retries} attempts")
                return False
            import time
            time.sleep(2)  # Wait 2 seconds before retrying
    return False

# Initialize database
init_database()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def send_email_brevo(to_email, subject, html_content, text_content=None):
    """Send email using Brevo API."""
    if not BREVO_API_KEY:
        print(f"Warning: BREVO_API_KEY not set. Email would be sent to: {to_email}")
        print(f"Subject: {subject}")
        print(f"Content: {text_content or html_content}")
        return False
    
    try:
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": to_email}],
            sender={"email": MAIL_DEFAULT_SENDER},
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )
        
        api_response = brevo_api_instance.send_transac_email(send_smtp_email)
        print(f"Email sent successfully to {to_email}. Message ID: {api_response.message_id}")
        return True
    except ApiException as e:
        print(f"Error sending email via Brevo: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error sending email: {e}")
        return False

def load_config():
    """Load configuration from either environment variables or a config file."""
    endpoint = os.getenv("AZURE_FORM_RECOGNIZER_ENDPOINT")
    key = os.getenv("AZURE_FORM_RECOGNIZER_KEY")

    if not endpoint or not key:
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        try:
            with open(config_path) as f:
                config = json.load(f)
                endpoint = config['azure']['endpoint']
                key = config['azure']['key']
        except FileNotFoundError:
            print("Warning: Azure Form Recognizer credentials not found")
            return None, None
    return endpoint, key

def initialize_azure_services():
    """Initialize Azure services with error handling and timeout."""
    global document_analysis_client, nogo_checker, blob_service
    
    # Initialize Azure Form Recognizer
    try:
        endpoint, key = load_config()
        if endpoint and key:
            document_analysis_client = DocumentAnalysisClient(
                endpoint=endpoint,
                credential=AzureKeyCredential(key)
            )
            print("Azure Form Recognizer initialized successfully")
        else:
            print("Warning: Azure Form Recognizer not initialized - missing credentials")
    except Exception as e:
        print(f"Warning: Azure Form Recognizer initialization failed: {e}")
    
    # Initialize NoGo checker
    try:
        csv_path = os.path.join(os.path.dirname(__file__), 'nogo_ingredients.csv')
        if os.path.exists(csv_path):
            nogo_checker = NoGoChecker(csv_path)
            print("NoGo checker initialized successfully")
        else:
            print(f"Warning: NoGo ingredients file not found at {csv_path}")
    except Exception as e:
        print(f"Warning: NoGo checker initialization failed: {e}")
    
    # Initialize Azure Blob Service
    try:
        print("Attempting to initialize Azure Blob Service...")
        blob_service = AzureBlobService()
        print("Azure Blob Service initialized successfully")
        
        # Debug: Check if Azure Blob credentials are loaded
        print(f"Azure Storage Account Name: {os.getenv('AZURE_STORAGE_ACCOUNT_NAME')}")
        print(f"Azure Storage Container Name: {os.getenv('AZURE_STORAGE_CONTAINER_NAME')}")
        print(f"Azure Storage Connection String configured: {'Yes' if os.getenv('AZURE_STORAGE_CONNECTION_STRING') else 'No'}")
        print(f"Is local mode: {blob_service.is_local if blob_service else 'N/A'}")
    except Exception as e:
        print(f"ERROR: Azure Blob Service initialization failed: {e}")
        print(f"Exception type: {type(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        blob_service = None

# Initialize Azure services in a separate thread to avoid blocking startup
def lazy_init_services():
    """Initialize services lazily to avoid blocking app startup."""
    import threading
    threading.Thread(target=initialize_azure_services, daemon=True).start()

# Start lazy initialization
lazy_init_services()


def normalize_text(text: str) -> str:
    """
    Normalize the text by removing stray quotes and similar characters.
    This function removes both straight and curly quotes.
    """
    replacements = {
        '"': '',
        '"': '',
        '"': '',
        "'": '',
        "'": '',
        "'": ''
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def tokenize_ingredients(ingredients_text: str) -> list:
    """
    Normalize the ingredients text and extract tokens from inside and outside of parentheses.

    Logic:
    1. Normalize the text and extract the substring after "INGREDIENTS:" (if available).
    2. Extract all text inside parentheses, split by commas, and clean the tokens.
    3. Remove all parentheses (and their content) from the text, then split the remaining text by commas.
    4. Return a combined list of tokens from both inside and outside the parentheses.
    """
    # Normalize text (assumes normalize_text() is defined elsewhere)
    ingredients_text = normalize_text(ingredients_text)

    # If there's an "INGREDIENTS:" marker, use only the text after it.
    match = re.search(r'INGREDIENTS:(.*)', ingredients_text, re.IGNORECASE)
    if match:
        ingredients_text = match.group(1)

    # Step 1: Extract tokens from inside parentheses.
    inside_tokens = []
    paren_groups = re.findall(r'\((.*?)\)', ingredients_text)
    for group in paren_groups:
        # Split by comma and clean each token.
        for token in group.split(','):
            token = token.strip().strip(string.punctuation)
            if token:
                inside_tokens.append(token)

    # Step 2: Remove all parentheses (and their content) from the text.
    outside_text = re.sub(r'\(.*?\)', '', ingredients_text)
    outside_tokens = []
    for token in outside_text.split(','):
        token = token.strip().strip(string.punctuation)
        if token:
            outside_tokens.append(token)

    # Combine tokens from inside and outside parentheses.
    all_tokens = inside_tokens + outside_tokens
    return all_tokens


def check_ingredients(ingredients_text: str, use_fuzzy: bool = False, fuzzy_threshold: int = 90, length_threshold: float = 0.7) -> dict:
    """
    Check the raw ingredients text against the no-go list.
    Only use exact matching (no fuzzy matching).
    Returns additional fields:
      - 'flagged_tokens': a list of tokens that triggered any match.
      - 'token_matches': a dict mapping each token to an array of match objects, 
                         where each match object has keys: 'nogo', 'score', and 'category'.
    """
    if not nogo_checker:
        return {
            'flag': 'Error',
            'reason': 'NoGo checker not available',
            'found_terms': {},
            'categories': [],
            'flagged_tokens': [],
            'token_matches': {}
        }
    
    print("\n=== CHECKING INGREDIENTS ===")
    print("Raw content for checking:", ingredients_text)

    tokens = tokenize_ingredients(ingredients_text)
    print("Tokenized ingredients:", tokens)

    found_terms = {}     # Aggregated matches (for overall recommendation)
    flagged_tokens = set()  # Unique tokens that triggered any match
    categories = set()
    token_matches = {}   # Detailed mapping: token -> list of match objects

    for token in tokens:
        token_lower = token.lower()
        matches_for_token = []  # list to collect match objects for this token
        token_matched = False
        for nogo_ingredient, info in nogo_checker.nogo_ingredients.items():
            nogo_lower = nogo_ingredient.lower()
            if token_lower == nogo_lower:
                match_obj = {"nogo": nogo_ingredient,
                             "score": 100, "category": info['category']}
                matches_for_token.append(match_obj)
                found_terms[nogo_ingredient] = 100
                categories.add(info['category'])
                token_matched = True
        if matches_for_token:
            token_matches[token] = matches_for_token
        if token_matched:
            flagged_tokens.add(token)

    is_nogo = bool(flagged_tokens)
    result = {
        'flag': 'NoGo' if is_nogo else 'Healthy',
        'reason': f'Contains concerning ingredients from categories: {", ".join(categories)}' if flagged_tokens else 'No concerning ingredients found',
        'found_terms': found_terms,
        'categories': list(categories),
        'flagged_tokens': list(flagged_tokens),
        'token_matches': token_matches  # New detailed mapping field
    }

    print("Final recommendation:", result)
    return result


def call_claude_sonnet_api(raw_text):
    """
    Send the OCR output to Claude Sonnet API for formatting and spell check.
    Returns the cleaned and formatted text as a JSON string with only the 'ingredients' field for food products.
    If the text is not from a food product, return a JSON error message.
    """
    api_key = os.getenv("CLAUDE_SONNET_API_KEY")
    if not api_key:
        raise ValueError("Claude Sonnet API key not set in environment variable 'CLAUDE_SONNET_API_KEY'.")

    endpoint = "https://api.anthropic.com/v1/messages"  # Update if your endpoint differs
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    prompt = (
        "You are an expert at reading food labels. "
        "Given the following OCR output from a product label, do the following: "
        "1. If the label is for a food product, extract and correct any spelling mistakes, and return ONLY a JSON string with one field: 'ingredients' (string, the cleaned and formatted ingredients list). "
        "2. For the 'ingredients' field, ensure the ingredients are separated by commas, even if the OCR output missed the commas. Use your best judgment to split the ingredients correctly and correct any spelling errors, so the output is perfect for downstream ingredient checking. "
        "3. If the label is NOT for a food product, return ONLY a JSON string with an 'error' field and a message, e.g. {\"error\": \"Not a food product label\"}. "
        "4. ####Do not include any other text or explanation, only the JSON string.\n\n"
        f"OCR Output:\n{raw_text}"
    )
    data = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 1024,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    response = requests.post(endpoint, headers=headers, json=data, timeout=30)
    response.raise_for_status()
    result = response.json()
    # Extract the cleaned text from the response
    cleaned_text = ""
    if "content" in result and isinstance(result["content"], list):
        cleaned_text = "\n".join([block.get("text", "") for block in result["content"]])
    elif "content" in result:
        cleaned_text = result["content"]
    else:
        cleaned_text = result.get("completion", "")
    return cleaned_text.strip()


def get_ingredient_explanation(ingredient_name, user=None):
    """
    Get a simple explanation about why an ingredient is concerning.
    Returns a plain text explanation that's personalized based on user's health conditions.
    Falls back to generic explanations if Claude API is not available.
    """
    api_key = os.getenv("CLAUDE_SONNET_API_KEY")
    
    # Fallback explanations for common concerning ingredients
    fallback_explanations = {
        "high fructose corn syrup": "High fructose corn syrup is linked to obesity, diabetes, and metabolic disorders due to its rapid absorption and effect on blood sugar levels.",
        "corn syrup": "Corn syrup is a highly processed sweetener that can contribute to blood sugar spikes and weight gain when consumed regularly.",
        "monosodium glutamate": "MSG can cause headaches and nausea in sensitive individuals, though it's generally recognized as safe by the FDA.",
        "msg": "MSG can cause headaches and nausea in sensitive individuals, though it's generally recognized as safe by the FDA.",
        "artificial colors": "Artificial food dyes have been linked to hyperactivity in children and may cause allergic reactions in sensitive individuals.",
        "artificial flavors": "Artificial flavors are synthetic compounds that may contain allergens and lack the nutritional benefits of natural flavor sources.",
        "sodium nitrite": "Sodium nitrite can form nitrosamines in the body, which are potentially carcinogenic compounds, especially when consumed in processed meats.",
        "sodium nitrate": "Sodium nitrate can convert to nitrites in the body and potentially form harmful nitrosamines, especially concerning in processed meats.",
        "bha": "BHA (butylated hydroxyanisole) is a preservative that may be carcinogenic and can cause allergic reactions in some people.",
        "bht": "BHT (butylated hydroxytoluene) is a preservative that may disrupt hormones and has been linked to potential health concerns.",
        "trans fat": "Trans fats raise bad cholesterol levels and increase the risk of heart disease, stroke, and diabetes.",
        "partially hydrogenated oil": "Partially hydrogenated oils contain trans fats, which are harmful to heart health and have been banned in many countries.",
        "hydrogenated oil": "Hydrogenated oils may contain trans fats and are highly processed, potentially contributing to cardiovascular health issues.",
        "aspartame": "Aspartame is an artificial sweetener that may cause headaches and other symptoms in sensitive individuals.",
        "sodium benzoate": "Sodium benzoate is a preservative that may form benzene (a carcinogen) when combined with vitamin C in certain conditions.",
        "potassium sorbate": "While generally safe, potassium sorbate can cause allergic reactions in sensitive individuals and may have preservative-related concerns.",
        "caramel color": "Caramel color, especially types III and IV, may contain potentially carcinogenic compounds formed during processing."
    }
    
    # If no API key, use fallback
    if not api_key:
        # Look for fallback explanation
        ingredient_lower = ingredient_name.lower()
        for key, explanation in fallback_explanations.items():
            if key in ingredient_lower or ingredient_lower in key:
                health_note = ""
                if user and hasattr(user, 'health_conditions') and user.health_conditions:
                    if 'diabetes' in user.health_conditions.lower() and 'sugar' in explanation.lower():
                        health_note = " This is especially concerning given your diabetes."
                    elif 'heart' in user.health_conditions.lower() and ('cholesterol' in explanation.lower() or 'heart' in explanation.lower()):
                        health_note = " This is particularly important given your heart condition."
                return explanation + health_note
        
        # Generic fallback
        return f"The ingredient '{ingredient_name}' is flagged as concerning in our database. It may contain additives, preservatives, or compounds that could have negative health effects when consumed regularly."

    # Try Claude API
    try:
        endpoint = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        # Build user profile from provided user data
        health_context = ""
        if user and hasattr(user, 'health_conditions') and user.health_conditions:
            health_context = f"The user has the following health conditions: {user.health_conditions}. "
        
        # Comprehensive scientific prompt with personalized health context
        system_prompt = """You are an expert food scientist, biochemist, and FDA regulatory specialist with deep knowledge of industrial food processing, chemical analysis, and nutritional biochemistry. Your role is to provide comprehensive, evidence-based explanations for why specific ingredients are NOGO, using peer-reviewed research, specific FDA regulations, detailed processing analysis, and biochemical mechanisms.

CORE SCIENTIFIC APPROACH:
For each NOGO ingredient, provide:
1. **Specific Scientific Evidence** - Cite research studies, biochemical mechanisms, quantitative data
2. **Detailed FDA Regulatory Analysis** - Reference specific CFR sections, GRAS loopholes, hidden ingredients
3. **Complete Processing Breakdown** - Step-by-step industrial processes, chemicals used, molecular changes
4. **Formulation Transparency** - Hidden chemicals, processing aids, undisclosed additives
5. **Whole Food Distance Analysis** - How many steps removed from natural state
6. **Biochemical Impact** - Specific metabolic pathways affected, nutrient interactions disrupted
7. **Nutrient Loss & Health Impact Analysis** - Quantify processing damage and health consequences

FDA LABELING COMPLIANCE REQUIREMENTS:

CRITICAL: Only reference ingredients/additives that appear on the ingredient list or are legally exempted from labeling.

**MUST BE LABELED (If Present):**
- Sulfites >10ppm (21 CFR 101.100(a)(4))
- All added sugars as separate ingredients
- Artificial colors and flavors
- Chemical preservatives above functional thresholds
- Allergens in any amount

**PROCESSING AIDS EXEMPT FROM LABELING:**
- Solvents below "functional level" (hexane <25ppm per 21 CFR 184.1555)
- Enzymes that don't remain in final product
- Filtration aids removed during processing
- pH adjustment chemicals neutralized during processing
- Processing temperatures and mechanical treatments

**REASONING RULE: Never assume unlisted ingredients unless legally exempted with CFR citation.**

EVIDENCE-BASED REASONING FRAMEWORK:

**ALWAYS INCLUDE:**
1. **Processing Damage**: Heat, mechanical, chemical treatment effects
2. **Quantified Nutrient Losses**: Specific percentages from whole food
3. **Missing Components**: Fiber, enzymes, cofactors removed
4. **Health Impact**: How nutrient losses affect human physiology
5. **Metabolic Consequences**: Biochemical pathways disrupted

**NEVER INCLUDE:**
- Speculation about unlisted ingredients
- Assumptions about preservatives/additives not on label
- "May contain" statements without regulatory basis

**VERIFICATION CHECKLIST:**
□ Is this processing damage inherent to the method?
□ Are mentioned chemicals legally exempt from labeling?
□ Am I quantifying nutrient losses from whole food?
□ Do I explain health impacts of missing nutrients?
□ Is this based on processing science vs assumptions?

NUTRIENT LOSS & HEALTH IMPACT ANALYSIS FRAMEWORK:

**CRITICAL FOCUS: Always compare processed ingredient to its whole food source, quantifying nutrient losses and explaining how these losses create adverse health impacts.**

**NUTRIENT LOSS QUANTIFICATION:**
For each processed ingredient, specify:
- Exact nutrients destroyed/removed during processing
- Percentage losses with before/after comparisons
- Processing step responsible for each nutrient loss
- Cumulative impact of multiple nutrient losses

**HEALTH IMPACT ANALYSIS:**
Explain how each lost nutrient affects human health:
- **Missing Fiber**: Gut microbiome disruption, blood sugar spikes, reduced satiety
- **Destroyed Vitamins**: Specific metabolic pathway interruptions
- **Eliminated Minerals**: Cofactor deficiencies affecting enzyme function
- **Lost Antioxidants**: Increased oxidative stress and inflammation
- **Removed Enzymes**: Digestive burden and nutrient malabsorption
- **Missing Phytonutrients**: Loss of protective plant compounds

**SYNERGISTIC NUTRIENT LOSS:**
Emphasize how whole foods provide nutrients in synergistic combinations:
- Vitamin C + bioflavonoids enhance absorption
- Fiber + minerals slow absorption and reduce glycemic impact
- Antioxidants + healthy fats improve bioavailability
- Enzymes + substrates aid natural digestion

**METABOLIC CONSEQUENCE FRAMEWORK:**
Connect nutrient losses to specific health problems:
- **Refined grains**: Fiber loss → gut dysbiosis → inflammation → metabolic syndrome
- **Processed oils**: Antioxidant loss → oxidative stress → cardiovascular disease
- **Fruit juices**: Fiber removal → blood sugar spikes → insulin resistance
- **Chemical preservatives**: Gut bacteria disruption → immune dysfunction

DEEP SCIENTIFIC EVIDENCE DATABASE:

**REFINED GRAINS (Semolina, White Flour, Wheat Flour):**
FDA Regulatory Alert: "Wheat" legally refers to refined wheat flour unless labeled "whole wheat." Steel roller milling removes bran (83% fiber) and germ (64% vitamin E, 26% thiamin). Nutrient losses: 80% vitamin E, 81% thiamin, 67% riboflavin, 80% niacin, 72% vitamin B6, 50% pantothenic acid, 86% folate, 84% iron, 68% magnesium, 78% zinc. Enrichment adds back only 4-5 synthetic nutrients vs 25+ naturally occurring compounds lost.

Health Impact: Missing fiber disrupts SCFAs production in gut microbiome, leading to inflammation and metabolic dysfunction. Lost B vitamins impair energy metabolism and nervous system function. Mineral deficiencies affect over 300 enzymatic reactions. High glycemic index (70-85) vs whole wheat (30-45) causes insulin spikes promoting diabetes risk.

Biochemical Impact: Phytic acid removal eliminates mineral-binding protection. Missing fiber allows rapid glucose absorption overwhelming normal metabolic pathways.

FDA Regulatory: 21 CFR 137.105 allows 'enriched flour' labeling despite 20+ nutrient losses. No requirement to disclose processing aids like chlorine dioxide bleaching.

**REFINED OILS (Vegetable Oil, Refined Olive Oil):**
Processing Steps: 1) Hexane extraction (petroleum-derived solvent), 2) Degumming with phosphoric acid, 3) Neutralization with sodium hydroxide, 4) Bleaching with acid-activated clay, 5) Deodorization at 450-470°F under vacuum.

Nutrient Losses: 90-95% vitamin E destruction, complete elimination of carotenoids, total loss of natural antioxidants (tocopherols, phenolic compounds).

Health Impact: Missing antioxidants allow cellular oxidative stress leading to cardiovascular disease and cancer. Trans fat formation (0.5-4.2g per 100g) disrupts cell membrane function. Omega-6:Omega-3 ratio 15-50:1 vs optimal 4:1 promotes systemic inflammation.

Biochemical Impact: Oxidized lipids trigger NF-κB inflammatory pathway. Lost vitamin E eliminates natural protection against lipid peroxidation.

FDA Regulatory: 21 CFR 184.1555 allows hexane as GRAS processing aid - no labeling required for residues up to 25ppm.

**CHEMICAL PRESERVATIVES (Sodium Benzoate, Potassium Sorbate):**
Mechanism: Sodium benzoate + ascorbic acid → benzene formation (carcinogen). FDA limit: 10ppb in beverages, but formation can exceed this in acidic conditions.

Health Impact: Gut microbiome disruption reduces Lactobacillus populations by 74-95%, compromising immune function and nutrient absorption. Mitochondrial DNA damage impairs cellular energy production.

Biochemical Impact: Preservatives interfere with normal bacterial fermentation in gut, reducing beneficial short-chain fatty acid production essential for colon health.

FDA Regulatory: 21 CFR 184.1733 GRAS status despite WHO classification of benzene as Group 1 carcinogen. No requirement to warn about benzene formation potential.

**NATURAL FLAVORS (The Biggest Deception):**
Formulation Reality: Single 'natural flavor' listing can contain 50-100 undisclosed chemicals:
- Flavor compounds (2-20 chemicals)
- Solvents: Propylene glycol, ethanol, triacetin
- Preservatives: BHT, BHA, TBHQ
- Emulsifiers: Polysorbate 80, lecithin
- Carriers: Maltodextrin, modified starch, silicon dioxide
- pH adjusters: Citric acid, sodium citrate

Nutrient Loss: Original food source reduced to <1% of final product, eliminating all beneficial compounds (antioxidants, fiber, vitamins, minerals) found in whole foods.

Health Impact: Chemical flavor compounds lack the nutritional matrix of whole foods, providing taste without health benefits while potentially disrupting normal taste perception.

FDA Regulatory Loophole: 21 CFR 101.22(i) allows 'incidental additives' exemption. Trade secret protection (21 CFR 20.61) prevents disclosure. Over 3,000 FDA-approved flavor chemicals can be hidden.

Processing: Chemical extraction using methylene chloride, supercritical CO2, or enzymatic hydrolysis destroys natural food matrix.

**ARTIFICIAL SWEETENERS (Aspartame, Sucralose, Acesulfame-K):**
Aspartame: Metabolizes to aspartic acid (40%), phenylalanine (40%), methanol (10%). Methanol oxidizes to formaldehyde then formic acid.

Health Impact: Studies show gut microbiome alterations (Bacteroides increase, Lactobacillus decrease) within 1 week, potentially affecting immune function and metabolism. Glucose intolerance induction in healthy subjects.

Nutrient Comparison: Unlike natural sweeteners in whole foods (fruit with fiber, antioxidants, vitamins), artificial sweeteners provide zero nutrition while potentially disrupting metabolic signaling.

FDA Regulatory: 21 CFR 172.804 ADI 50mg/kg body weight, but neurological effects reported at lower doses in sensitive individuals.

**MODIFIED STARCHES:**
Chemical Modifications: Cross-linking with phosphorus oxychloride, acetylation with acetic anhydride, hydroxypropylation with propylene oxide.

Nutrient Loss: Complete removal from whole food source (grains, potatoes) eliminates fiber, protein, vitamins, minerals, leaving only modified carbohydrate.

Health Impact: Missing natural food matrix means rapid glucose absorption without beneficial nutrients. Modified molecular structure creates compounds not found in traditional food, with unknown long-term effects.

Molecular Changes: Creates resistant starch types not found in nature. Digestive enzyme resistance altered vs native starches.

FDA Regulatory: 21 CFR 172.892 allows multiple chemical modifications without specific labeling of modification type.

**ENRICHED/FORTIFIED PRODUCTS:**
Nutrient Loss: Original whole food nutrients destroyed, then synthetic versions added back. Example: Whole wheat → refined flour loses 25+ nutrients → only 4-5 synthetic nutrients added.

Health Impact: Synthetic nutrients lack cofactors and stereoisomers of natural forms. Iron fumarate absorption 3-5% vs heme iron 15-35%. Synthetic vitamin E (dl-alpha-tocopherol) has 50% bioactivity of natural form.

Biochemical Impact: Folic acid vs natural folate metabolism differs - synthetic form may mask B12 deficiency. Missing nutrient synergies reduce overall nutritional effectiveness.

FDA Regulatory: 21 CFR 104.20 requires fortification disclosure but not synthetic vs natural distinction.

FDA GRAIN LABELING DECEPTION FRAMEWORK:

CRITICAL: FDA naming conventions allow refined grains to appear natural on ingredient lists. Understanding these regulatory tricks is essential for proper ingredient evaluation:

**REFINED BY DEFAULT (Unless Specified as "Whole"):**
- "Wheat" = Legally defined as refined wheat flour (missing bran and germ)
- "Wheat flour" = Refined flour despite natural appearance
- "Semolina" = Refined durum wheat (bran and germ removed)
- "Corn" = May be degerminated (refined) unless labeled "whole corn"
- "Rice" = White/refined rice unless specified as "brown rice" or colored varieties
- "Rye" = Refined unless labeled "whole rye" or "rye berries"
- "Spelt" = Can be refined unless labeled "whole spelt"
- "Farro" = Refined if labeled "pearled farro"

**TYPICALLY WHOLE (Due to Processing Economics):**
- Amaranth, buckwheat, quinoa, millet = Almost invariably whole grain
- Teff = Too small to mill, always whole grain
- Freekeh = Including cracked freekeh, almost invariably whole
- Wild rice = Almost invariably whole

**LABELING ALERT TERMS:**
- "Degerminated" = Germ removed (refined)
- "Pearled" = Bran removed (refined)
- "Enriched" = Refined then synthetic nutrients added back
- "Whole" = Must appear before grain name for true whole grain

Incorporate this regulatory context when explaining grain-based NOGO ingredients to expose FDA labeling deceptions.

DEEP FDA REGULATORY ANALYSIS:

**GRAS Loopholes:**
- Self-GRAS determination allows companies to approve their own additives
- No FDA review required for GRAS substances
- Trade secret protection prevents ingredient disclosure
- 'Processing aid' exemption removes labeling requirements

**Hidden Ingredient Allowances:**
- 21 CFR 101.100(a)(3): Incidental additives exemption
- Solvent residues below 'functional level' not required on labels
- Processing aids that don't remain in final product exempt
- Flavor component chemicals protected as trade secrets

**Labeling Deceptions:**
- 'Natural' has no legal definition for processed foods
- 'Organic' allows 5% non-organic ingredients
- 'No artificial flavors' while using 'natural flavors' (chemically identical)
- Trans fat 'zero' allows up to 0.5g per serving

WHOLE FOOD DISTANCE ANALYSIS:

**Distance Measurement Framework:**
- Level 1: Whole food (apple)
- Level 2: Mechanical processing (apple juice)
- Level 3: Thermal processing (pasteurized apple juice)
- Level 4: Chemical extraction (apple flavor)
- Level 5: Synthetic recreation (artificial apple flavor)

**Processing Step Counting:**
Semolina: Wheat → cleaning → tempering → milling → sifting → bleaching = 5 major steps from whole grain
Vegetable Oil: Seeds → cleaning → crushing → hexane extraction → degumming → neutralizing → bleaching → deodorizing = 7 major steps
Natural Flavor: Fruit → crushing → distillation → chemical separation → solvent extraction → concentration = 5+ steps

BIOCHEMICAL PATHWAY DISRUPTION:

**Nutrient Synergy Loss:**
Refined grains lose fiber-nutrient binding that slows absorption and reduces glycemic impact. Vitamin C + bioflavonoids synergy lost in synthetic ascorbic acid. Whole food nutrients work together - processing destroys these relationships.

**Metabolic Pathway Interference:**
High fructose disrupts normal glucose metabolism through fructokinase bypass of phosphofructokinase regulation. Trans fats interfere with delta-6-desaturase enzyme affecting essential fatty acid metabolism. Missing cofactors impair enzymatic reactions.

**Gut Microbiome Impact:**
Emulsifiers (carrageenan, polysorbate 80) thin protective mucus layer. Artificial sweeteners alter microbial composition within 11 days of consumption. Missing prebiotic fiber starves beneficial bacteria.

QUANTITATIVE NUTRITIONAL DATA:

**Specific Nutrient Losses in Processing:**
- White rice: 67% B3, 80% B1, 90% B6, 60% iron, 75% fiber
- Refined sugar: 100% of all micronutrients from sugar cane/beet
- Pasteurization: 10-50% vitamin C loss depending on temperature/time
- Canning: 20-80% water-soluble vitamin loss
- Fruit juice: 100% fiber loss, 30-70% antioxidant reduction

FDA LABELING TRICKS TO EXPOSE:

**Grain Labeling Deception:**
- "Wheat" = FDA legally defines as refined flour (bran and germ removed)
- "Whole wheat" = Actual whole grain with all components intact
- "Semolina" = Refined durum wheat despite appearing traditional
- "Degerminated corn" = Processed corn with nutrient-rich germ removed
- "Pearled farro" = Bran removed, making it refined grain

**"Whole" vs Refined Distinction:**
Always specify FDA naming deception: "Semolina is refined durum wheat despite natural appearance. FDA allows 'wheat' to legally mean refined flour, while 'whole wheat' indicates true whole grain with bran, germ, and endosperm intact."

**"Natural" vs Synthetic:**
- "Natural flavor" = NOGO (still chemically processed)
- "Vanilla bean" = GO (whole food form)

**Oil Processing Indicators:**
- "Extra virgin" = GO (cold-pressed, nutrients intact)
- "Refined" = NOGO (high heat, chemical processing)

**Enrichment Red Flags:**
- "Enriched" = NOGO (nutrients removed then synthetic versions added)
- "Fortified" = NOGO (artificial supplementation)

For each NOGO classification, connect the specific processing method to the nutritional consequences and health implications, exposing how FDA labeling can disguise highly processed ingredients.

COMPREHENSIVE TRAINING DATA REFERENCE LISTS:

IMPORTANT: Always check these specific ingredient classifications FIRST before applying general pattern rules. These override any general logic.

CRITICAL NOGO INGREDIENTS (Despite seeming natural/traditional):

Sweeteners & Syrups (NOGO):
- Honey (without 'raw' qualifier), syrup, coconut nectar, maple syrup
- Sugar, Sucrose, Glucose, Fructose, Galactose, Lactose, Maltose, Dextrose
- All syrups and refined sweeteners

Oils (NOGO unless specifically qualified):
- vegetable oil, olive oil, coconut oil, sunflower oil, sesame oil, almond oil
- REFINED OLIVE OIL, refined coconut oil
- Any oil without 'extra virgin,' 'cold pressed,' or 'unrefined' qualifiers

Wheat & Grain Products (ALL NOGO):
- SEMOLINA, DURUM WHEAT SEMOLINA, wheat, WHEAT FLOUR
- enriched wheat flour, Unbleached Enriched Wheat Flour
- CRACKED WHEAT, HARD AMBER DURUM WHEAT, UNBLEACHED WHEAT FLOUR
- starch, lecithin, carrageenan

Chemical Additives (NOGO):
- SODIUM BENZOATE, Potassium Sorbate, PHOSPHATE, Sulfur Dioxide, Sulfites
- Flavor (unqualified), Acid, Glycerin, vegetable glycerin
- MSG, artificial flavors, preservatives

CRITICAL GO INGREDIENTS (Despite containing trigger words):

Acceptable Oils (GO - with specific qualifiers):
- extra virgin olive oil, Cold pressed Flaxseed oil, Unrefined flaxseed oil
- cold pressed sunflower oil, unrefined sunflower oil, extra virgin Avocado Oil
- extra virgin sunflower oil, cold pressed walnut oil, extra virgin sesame oil
- cold pressed sesame oil, unrefined sesame oil, cold pressed almond oil
- extra virgin coconut oil

Natural Sweeteners (GO - with specific qualifiers):
- raw honey (only when 'raw' is specified)

Whole Foods with Confusing Names (GO):
- Sugar snap peas, Sugar Apple, Sugar Baby Watermelon, Sugar Palm
- vanilla bean, vanilla bean powder (whole forms)
- Saltbush, Oil Palm (whole plant foods)

Traditional Preparations (GO):
- Dried herbs, fermented vegetables, stone-ground items
- Powders from whole foods (vanilla bean powder)

CLASSIFICATION OVERRIDE PROTOCOL:
1. Check ingredient against specific training data from uploaded files FIRST
2. Exact matches override all pattern-based rules
3. For oils: GO only if contains 'extra virgin,' 'cold pressed,' or 'unrefined'
4. For honey: GO only if contains 'raw'
5. ALL wheat products are NOGO regardless of processing description
6. ALL refined sweeteners are NOGO regardless of source

EDGE CASE HANDLING:
- 'Coconut oil' → Check for 'refined' (NOGO) vs 'cold-pressed' (GO)
- 'Apple juice' → Check for 'concentrate' (NOGO) vs 'fresh-pressed' (GO)
- 'Natural flavor' → Always NOGO (heavily processed despite natural origin)
- 'Stevia extract' → NOGO (isolated compounds despite natural source)
- 'Monk fruit extract' → NOGO (concentrated compounds, not whole fruit)

For unknown ingredients: Default to NOGO if chemical compound pattern detected, flag whole foods not in training data for review, assign confidence score < 6 for unknowns.

Handle variations in capitalization, abbreviations, spelling variants, and parenthetical information by focusing on main ingredient while noting additives.

REASONING OUTPUT REQUIREMENTS:

1. **Scientific Evidence**: Cite specific studies, mechanisms, quantitative data
2. **FDA Regulatory**: Reference CFR sections, loopholes, hidden ingredients
3. **Processing Details**: Step-by-step industrial processes, chemicals used
4. **Formulation Transparency**: Hidden chemicals in flavor systems (only if legally exempt)
5. **Whole Food Steps**: Count processing steps from natural state
6. **Biochemical Impact**: Specific pathways and metabolic effects
7. **Quantitative Data**: Nutrient loss percentages, chemical concentrations
8. **Regulatory Deception**: How labeling hides processing reality
9. **Nutrient Loss Analysis**: Compare to whole food source with specific losses
10. **Health Impact**: Connect nutrient losses to physiological consequences

For each NOGO ingredient, provide comprehensive analysis covering all these aspects while maintaining scientific accuracy, regulatory transparency, and FDA labeling compliance."""

        user_prompt = f"""Provide comprehensive, evidence-based scientific reasoning for why the ingredient "{ingredient_name}" is concerning for health. Include:

1. Specific scientific evidence (studies, mechanisms, quantitative data)
2. Detailed FDA regulatory analysis (CFR references, loopholes, hidden ingredients)
3. Complete processing breakdown (step-by-step industrial processes, chemicals used)
4. Formulation transparency (hidden chemicals, processing aids, undisclosed additives - only if legally exempt from labeling)
5. Whole food distance analysis (processing steps from natural state)
6. Biochemical impact (metabolic pathways affected, nutrient interactions disrupted)
7. Nutrient loss & health impact analysis (quantify losses from whole food source and explain health consequences)

{health_context}If relevant to the user's health conditions, emphasize specific concerns for those conditions.

Provide thorough scientific analysis while keeping explanations accessible. Keep response focused and complete - approximately 3-4 key sentences covering the most critical scientific points without cutting off mid-sentence.

IMPORTANT: Only reference chemicals/additives that appear on ingredient lists OR are legally exempt from labeling with CFR citation. Never assume unlisted ingredients are present.

CRITICAL RESPONSE LENGTH REQUIREMENT: Your response MUST be less than 4 sentences total. Focus on the single most critical scientific concern with the highest health impact. Be concise but comprehensive within this strict limit."""
        
        data = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 500,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_prompt}
            ]
        }
        
        response = requests.post(endpoint, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        # Extract the explanation from the response
        explanation = ""
        if "content" in result and isinstance(result["content"], list):
            explanation = "\n".join([block.get("text", "") for block in result["content"]])
        elif "content" in result:
            explanation = result["content"]
        else:
            explanation = result.get("completion", "")
        
        return explanation.strip() if explanation.strip() else f"The ingredient '{ingredient_name}' is flagged as concerning in our database and may have potential health risks."
        
    except Exception as e:
        print(f"Claude API error: {e}")
        # Fall back to generic explanation
        return f"The ingredient '{ingredient_name}' is flagged as concerning in our database. It may contain additives, preservatives, or compounds that could have negative health effects when consumed regularly."


def validate_image_with_claude(image_data):
    """
    Use Claude Sonnet to validate if the image contains a food product label.
    Returns True if it's a food product, False otherwise.
    """
    api_key = os.getenv("CLAUDE_SONNET_API_KEY")
    if not api_key:
        print("Warning: Claude Sonnet API key not set, skipping image validation")
        return True  # Skip validation if no API key
    
    try:
        # Detect image format and convert to base64 for Claude Vision
        import base64
        from PIL import Image
        import io
        
        # Detect image format
        image = Image.open(io.BytesIO(image_data))
        format_map = {
            'JPEG': 'image/jpeg',
            'PNG': 'image/png',
            'WEBP': 'image/webp',
            'GIF': 'image/gif',
            'BMP': 'image/bmp',
            'TIFF': 'image/tiff'
        }
        media_type = format_map.get(image.format, 'image/jpeg')  # Default to JPEG
        print(f"Detected image format: {image.format}, using media_type: {media_type}")
        
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        endpoint = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        prompt = (
            "You are an expert at identifying food product labels. "
            "Look at this image and determine if it contains a food product label. "
            "A food product label should contain: "
            "- Nutrition facts or nutritional information "
            "- Ingredients list "
            "- Food product packaging or label "
            "- Product name that indicates it's food "
            "\n"
            "If this is a food product label, respond with: {\"is_food\": true}"
            "If this is NOT a food product label (e.g., electronics, clothing, books, etc.), respond with: {\"is_food\": false, \"reason\": \"brief reason\"}"
            "\n"
            "Only respond with the JSON, no additional text."
        )
        
        data = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 150,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_base64
                            }
                        }
                    ]
                }
            ]
        }
        
        response = requests.post(endpoint, headers=headers, json=data, timeout=30)
        print(f"Claude API Response Status: {response.status_code}")
        print(f"Claude API Response Headers: {dict(response.headers)}")
        if response.status_code != 200:
            print(f"Claude API Error Response: {response.text}")
        response.raise_for_status()
        result = response.json()
        
        # Extract the response text
        response_text = ""
        if "content" in result and isinstance(result["content"], list):
            response_text = "\n".join([block.get("text", "") for block in result["content"]])
        elif "content" in result:
            response_text = result["content"]
        else:
            response_text = result.get("completion", "")
        
        # Parse the JSON response
        import json
        try:
            validation_result = json.loads(response_text)
            is_food = validation_result.get("is_food", True)  # Default to True if parsing fails
            print(f"Image validation result: {validation_result}")
            return is_food
        except json.JSONDecodeError:
            print(f"Warning: Could not parse Claude response: {response_text}")
            return False  # Default to False if parsing fails - be conservative
            
    except Exception as e:
        print(f"Warning: Image validation failed: {str(e)}")
        return False  # Default to False if validation fails - be conservative


@app.route('/')
@login_required
def home():
    return render_template('index.html')


@app.route('/dashboard')
@login_required
def dashboard():
    scans = Scan.query.filter_by(user_id=current_user.id).order_by(Scan.timestamp.desc()).all()
    
    # Generate fresh image URLs on-demand for each scan
    for scan in scans:
        if scan.blob_name:
            try:
                scan.image_url = blob_service.get_image_url(scan.blob_name)
            except Exception as e:
                print(f"Error generating image URL for scan {scan.id}: {str(e)}")
                scan.image_url = None
    
    return render_template('dashboard.html', scans=scans)


@app.route('/process', methods=['POST'])
@login_required
def process_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400

    try:
        image = request.files['image']
        temp_path = None

        # --- Validate image with Claude BEFORE processing (cost optimization) ---
        try:
            # Read the uploaded file for validation
            image.seek(0)  # Reset file pointer
            image_data = image.read()
            
            # Validate if it's a food product
            is_food_product = validate_image_with_claude(image_data)
            if not is_food_product:
                return jsonify({
                    'error': 'not_food_product',
                    'message': 'Please Scan a Food Product',
                    'description': 'This image does not appear to contain a food label. Please try again with a clear photo of food packaging.'
                }), 400
            
            print("✅ Image validated as food product, proceeding with OCR...")
            
            # Reset file pointer for OCR processing
            image.seek(0)
        except Exception as e:
            print(f"Warning: Image validation failed: {str(e)}")
            # Continue without validation if Claude API fails
            image.seek(0)

        # Save the uploaded image to a temporary file.
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp:
            temp_path = temp.name
            image.save(temp_path)

                    # Process with Azure Form Recognizer.
        if not document_analysis_client:
            return jsonify({'error': 'Azure Form Recognizer not available. Please check configuration.'}), 500
            
        with open(temp_path, "rb") as image_file:
            poller = document_analysis_client.begin_analyze_document(
                "prebuilt-layout", image_file
            )
            result = poller.result()

        # Get raw content from the recognized document.
        raw_content = result.content
        print("\nRaw Content from Azure:", raw_content)

        # Guard: If OCR result is empty or whitespace, return error
        if not raw_content or not raw_content.strip():
            return jsonify({'error': 'No text detected. Please try again with a clear food label.'}), 400

        # NEW: Send to Claude Sonnet API for formatting and spell check
        try:
            cleaned_content = call_claude_sonnet_api(raw_content)
            print("\nCleaned Content from Claude Sonnet:", cleaned_content)
        except Exception as e:
            print(f"Error calling Claude Sonnet API: {str(e)}")
            cleaned_content = raw_content  # Fallback to raw if Claude fails

        # Guard: If cleaned_content is empty or whitespace, return error
        if not cleaned_content or not cleaned_content.strip():
            return jsonify({'error': 'No ingredients detected. Please try again with a clear food label.'}), 400

        # Get recommendation using our tokenized exact matching.
        if not nogo_checker:
            return jsonify({'error': 'NoGo checker not available. Please check configuration.'}), 500
            
        recommendation = check_ingredients(
            cleaned_content, use_fuzzy=True, fuzzy_threshold=85)

        # Retrieve debug information if available.
        debug_info = nogo_checker.debug_check(cleaned_content) if nogo_checker else {'normalized_text': '', 'matches': []}

        # Add tokenized ingredients for frontend use
        tokenized_ingredients = tokenize_ingredients(cleaned_content) if cleaned_content else []
        
        response_data = {
            'raw_content': cleaned_content,
            'tokenized_ingredients': tokenized_ingredients,
            'recommendation': recommendation,
            'debug_info': {
                'normalized_text': debug_info.get('normalized_text', ''),
                'matches': debug_info.get('matches', [])
            }
        }

        # --- Store image in Azure Blob Storage ---
        image_url = None
        blob_name = None
        
        if blob_service and 'image' in request.files:
            try:
                file = request.files['image']
                if file and file.filename:
                    # Read the uploaded file
                    file.seek(0)  # Reset file pointer
                    image_data = file.read()
                    
                    # Upload to Azure Blob Storage
                    upload_result = blob_service.upload_image(
                        image_data=image_data,
                        user_email=current_user.email,
                        original_filename=file.filename
                    )
                    image_url = upload_result['url']
                    blob_name = upload_result['blob_name']
                    
                    print(f"Image uploaded successfully: {image_url}")
            except Exception as e:
                print(f"Warning: Failed to upload image to Azure Blob: {str(e)}")
                # Continue without image storage

        # --- Store scan in DB ---
        scan = Scan(
            user_id=current_user.id,
            scan_data=response_data,
            comments=None,  # Can be updated later
            image_url=image_url,
            blob_name=blob_name
        )
        db.session.add(scan)
        db.session.commit()

        # Add scan_id to response data for comment functionality
        response_data['scan_id'] = scan.id

        return jsonify(response_data)

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


@app.route('/debug/ingredients')
def debug_ingredients():
    """Endpoint to test ingredient processing."""
    test_text = request.args.get('text', '')
    tokens = tokenize_ingredients(test_text)
    
    if not nogo_checker:
        return jsonify({'error': 'NoGo checker not available'}), 500
        
    debug_info = nogo_checker.debug_check(test_text)

    found_terms = set()
    categories = set()
    for token in tokens:
        token_lower = token.lower()
        for nogo_ingredient, cat in nogo_checker.nogo_ingredients.items():
            if token_lower == nogo_ingredient.lower():
                found_terms.add(nogo_ingredient)
                categories.add(str(cat))
    is_nogo = bool(found_terms)

    return jsonify({
        'raw_text': test_text,
        'tokenized': tokens,
        'normalized_text': debug_info.get('normalized_text', ''),
        'matches': debug_info.get('matches', []),
        'is_nogo': is_nogo,
        'found_terms': list(found_terms),
        'categories': list(categories)
    })


@app.route('/debug/azure-blob')
def debug_azure_blob():
    """Debug endpoint to check Azure Blob service status."""
    global blob_service
    
    debug_info = {
        'environment_variables': {
            'AZURE_STORAGE_ACCOUNT_NAME': os.getenv('AZURE_STORAGE_ACCOUNT_NAME'),
            'AZURE_STORAGE_CONTAINER_NAME': os.getenv('AZURE_STORAGE_CONTAINER_NAME'),
            'AZURE_STORAGE_CONNECTION_STRING_CONFIGURED': bool(os.getenv('AZURE_STORAGE_CONNECTION_STRING')),
            'AZURE_STORAGE_ACCOUNT_KEY_CONFIGURED': bool(os.getenv('AZURE_STORAGE_ACCOUNT_KEY'))
        },
        'blob_service': {
            'initialized': blob_service is not None,
            'is_local': blob_service.is_local if blob_service else None,
            'container_name': blob_service.container_name if blob_service else None
        }
    }
    
    # Try to test container access if blob service is initialized
    if blob_service and not blob_service.is_local:
        try:
            container_client = blob_service.blob_service_client.get_container_client(blob_service.container_name)
            properties = container_client.get_container_properties()
            debug_info['container_test'] = {
                'success': True,
                'last_modified': properties.last_modified.isoformat() if properties.last_modified else None
            }
        except Exception as e:
            debug_info['container_test'] = {
                'success': False,
                'error': str(e)
            }
    
    return jsonify(debug_info)


# --- Auth Routes ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        first_name = request.form['first_name'].strip()
        last_name = request.form.get('last_name', '').strip() or None
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('register'))
        
        if not first_name:
            flash('First name is required.', 'danger')
            return redirect(url_for('register'))
            
        user = User(email=email, first_name=first_name, last_name=last_name)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=True)  # Make session permanent
            from flask import session
            session.permanent = True
            flash('Logged in successfully.', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password.', 'danger')
    return render_template('login.html')  # TODO: Create this template

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        tab = request.form.get('tab', 'basic')
        
        if tab == 'basic':
            # Handle basic info update
            first_name = request.form['first_name'].strip()
            last_name = request.form.get('last_name', '').strip() or None
            email = request.form['email'].strip().lower()
            date_of_birth_str = request.form.get('date_of_birth', '').strip()
            
            if not first_name:
                flash('First name is required.', 'danger')
                return redirect(url_for('profile'))
            
            # Check if email is already taken by another user
            existing_user = User.query.filter_by(email=email).first()
            if existing_user and existing_user.id != current_user.id:
                flash('Email already registered by another user.', 'danger')
                return redirect(url_for('profile'))
            
            # Parse date of birth
            date_of_birth = None
            if date_of_birth_str:
                try:
                    from datetime import datetime
                    date_of_birth = datetime.strptime(date_of_birth_str, '%Y-%m-%d').date()
                except ValueError:
                    flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
                    return redirect(url_for('profile'))
            
            # Update user profile
            current_user.first_name = first_name
            current_user.last_name = last_name
            current_user.email = email
            current_user.date_of_birth = date_of_birth
            
            db.session.commit()
            flash('Profile updated successfully.', 'success')
            return redirect(url_for('profile'))
            
        elif tab == 'preferences':
            # Handle preferences update
            health_conditions = request.form.get('health_conditions', '').strip() or None
            
            # Update user preferences
            current_user.health_conditions = health_conditions
            
            db.session.commit()
            flash('Health conditions saved successfully! Your ingredient explanations will now be personalized.', 'success')
            return redirect(url_for('profile') + '#preferences')
    
    return render_template('profile.html')

# --- Password Reset ---
# Setup for token generation
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        user = User.query.filter_by(email=email).first()
        if user:
            # Generate token
            token = serializer.dumps(user.email, salt='password-reset-salt')
            user.reset_token = token
            from datetime import datetime, timedelta
            user.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()
            # Send email with reset link using Brevo
            reset_url = url_for('reset_password', token=token, _external=True)
            print(f"Password reset link: {reset_url}")  # Always print for local testing
            
            subject = "Password Reset Request - Food Label Scanner"
            html_content = f"""
            <html>
            <body>
                <h2>Password Reset Request</h2>
                <p>Hello,</p>
                <p>You have requested to reset your password for the Food Label Scanner application.</p>
                <p>Click the following link to reset your password:</p>
                <p><a href="{reset_url}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Reset Password</a></p>
                <p>Or copy and paste this link into your browser:</p>
                <p>{reset_url}</p>
                <p>This link will expire in 1 hour.</p>
                <p>If you did not request this password reset, please ignore this email.</p>
                <br>
                <p>Best regards,<br>Food Label Scanner Team</p>
            </body>
            </html>
            """
            text_content = f"""Password Reset Request

Hello,

You have requested to reset your password for the Food Label Scanner application.

Click the following link to reset your password:
{reset_url}

This link will expire in 1 hour.

If you did not request this password reset, please ignore this email.

Best regards,
Food Label Scanner Team"""
            
            send_email_brevo(user.email, subject, html_content, text_content)
            flash('Password reset link sent to your email.', 'info')
        else:
            flash('If that email is registered, a reset link has been sent.', 'info')
        return redirect(url_for('login'))
    return render_template('forgot_password.html')  # TODO: Create this template

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=3600)
    except (SignatureExpired, BadSignature):
        flash('The password reset link is invalid or has expired.', 'danger')
        return redirect(url_for('forgot_password'))
    user = User.query.filter_by(email=email).first()
    if not user or user.reset_token != token:
        flash('Invalid or expired reset link.', 'danger')
        return redirect(url_for('forgot_password'))
    if request.method == 'POST':
        password = request.form['password']
        user.set_password(password)
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()
        flash('Your password has been reset. Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('reset_password.html')  # TODO: Create this template

@app.route('/scan/<int:scan_id>')
@login_required
def scan_detail(scan_id):
    scan = Scan.query.get_or_404(scan_id)
    if scan.user_id != current_user.id:
        abort(403)
    
    # Migration: Convert legacy comments to ScanComment entries
    if scan.comments and scan.comments.strip() and not scan.scan_comments:
        try:
            legacy_comment = ScanComment(
                scan_id=scan.id,
                comment_text=scan.comments,
                timestamp=scan.timestamp  # Use the original scan timestamp
            )
            db.session.add(legacy_comment)
            # Clear the legacy comment field
            scan.comments = None
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Error migrating legacy comment: {e}")
    
    # Migration: Add tokenized_ingredients for legacy scans that don't have it
    scan_data_modified = False
    if scan.scan_data and not scan.scan_data.get('tokenized_ingredients'):
        raw_content = scan.scan_data.get('raw_content')
        if raw_content:
            try:
                tokenized_ingredients = tokenize_ingredients(raw_content)
                scan.scan_data['tokenized_ingredients'] = tokenized_ingredients
                scan_data_modified = True
                print(f"Added tokenized_ingredients to scan {scan.id}: {tokenized_ingredients}")
            except Exception as e:
                print(f"Error tokenizing ingredients for scan {scan.id}: {e}")
    
    if scan_data_modified:
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Error saving tokenized ingredients: {e}")
    
    # Generate fresh image URL on-demand
    if scan.blob_name:
        try:
            scan.image_url = blob_service.get_image_url(scan.blob_name)
        except Exception as e:
            print(f"Error generating image URL for scan {scan.id}: {str(e)}")
            scan.image_url = None
    
    return render_template('scan_detail.html', scan=scan)

@app.route('/scan/<int:scan_id>/comment', methods=['POST'])
@login_required
def edit_comment(scan_id):
    scan = Scan.query.get_or_404(scan_id)
    if scan.user_id != current_user.id:
        abort(403)
    comment = request.form.get('comment', '').strip()
    scan.comments = comment
    db.session.commit()
    flash('Comment updated successfully!', 'success')
    return redirect(url_for('scan_detail', scan_id=scan_id))

@app.route('/scan/<int:scan_id>/comment/add', methods=['POST'])
@login_required
def add_comment(scan_id):
    try:
        scan = Scan.query.get_or_404(scan_id)
        if scan.user_id != current_user.id:
            abort(403)
        
        new_comment_text = request.form.get('new_comment', '').strip()
        if new_comment_text:
            new_comment = ScanComment(
                scan_id=scan.id,
                comment_text=new_comment_text
            )
            db.session.add(new_comment)
            db.session.commit()
            flash('Comment added successfully!', 'success')
        else:
            flash('Comment cannot be empty.', 'danger')
            
    except Exception as e:
        db.session.rollback()
        flash('Failed to add comment.', 'danger')
    
    return redirect(url_for('scan_detail', scan_id=scan_id) + '#comments')

@app.route('/scan/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_scan_comment(comment_id):
    """Delete an individual scan comment."""
    try:
        comment = ScanComment.query.get_or_404(comment_id)
        scan = Scan.query.get_or_404(comment.scan_id)
        
        # Check if the user owns the scan
        if scan.user_id != current_user.id:
            abort(403)
        
        db.session.delete(comment)
        db.session.commit()
        
        # Check if this is an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True})
        
        flash('Comment deleted successfully!', 'success')
        return redirect(url_for('scan_detail', scan_id=scan.id))
    except Exception as e:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': str(e)}), 500
        flash('Failed to delete comment.', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/scan/<int:scan_id>/comment/delete', methods=['POST'])
@login_required
def delete_comment(scan_id):
    try:
        scan = Scan.query.get_or_404(scan_id)
        if scan.user_id != current_user.id:
            abort(403)
        scan.comments = None
        db.session.commit()
        
        # Check if this is an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True})
        
        flash('Comment deleted.', 'success')
        return redirect(url_for('dashboard'))
    except Exception as e:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': str(e)}), 500
        flash('Failed to delete comment.', 'danger')
        return redirect(url_for('dashboard'))

# Route to serve local images for testing
@app.route('/local_storage/images/<path:filename>')
def serve_local_image(filename):
    """Serve local images for testing purposes."""
    local_storage_dir = os.path.join(os.path.dirname(__file__), '..', 'local_storage', 'images')
    return send_from_directory(local_storage_dir, filename)

# API route for ingredient explanations
@app.route('/api/ingredient-explanation', methods=['POST'])
@login_required
def get_ingredient_explanation_api():
    """
    API endpoint to get explanations for concerning ingredients using Claude AI.
    Expects JSON payload with 'ingredient' field.
    Uses current user's profile for personalized explanations.
    """
    try:
        data = request.get_json()
        if not data or 'ingredient' not in data:
            return jsonify({'error': 'Missing ingredient parameter'}), 400
        
        ingredient_name = data['ingredient'].strip()
        if not ingredient_name:
            return jsonify({'error': 'Ingredient name cannot be empty'}), 400
        
        # Get explanation from Claude with user's profile
        explanation = get_ingredient_explanation(ingredient_name, current_user)
        
        return jsonify({
            'ingredient': ingredient_name,
            'explanation': explanation
        })
        
    except Exception as e:
        print(f"Error getting ingredient explanation: {e}")
        return jsonify({'error': 'Failed to get ingredient explanation'}), 500

# Session refresh API endpoint
@app.route('/api/refresh-session', methods=['POST'])
@login_required
def refresh_session():
    """
    API endpoint to refresh the user's session.
    Returns the new session expiry time.
    """
    try:
        from flask import session
        from datetime import datetime
        
        # Refresh the session by updating the modified flag
        session.permanent = True
        session.modified = True
        
        # Touch the session to reset its expiry
        # This forces Flask to update the session cookie with a new expiry time
        session['_refresh_timestamp'] = datetime.now().isoformat()
        
        # Calculate new expiry time
        expiry_time = datetime.now() + app.config['PERMANENT_SESSION_LIFETIME']
        
        return jsonify({
            'status': 'success',
            'message': 'Session refreshed successfully',
            'expires_at': expiry_time.isoformat(),
            'expires_in_seconds': int(app.config['PERMANENT_SESSION_LIFETIME'].total_seconds())
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to refresh session: {str(e)}'}), 500

@app.route('/api/save-comment', methods=['POST'])
@login_required
def save_comment_api():
    """
    API endpoint to save comments for scans.
    Expects JSON payload with 'scan_id' and 'comment' fields.
    """
    try:
        data = request.get_json()
        if not data or 'scan_id' not in data or 'comment' not in data:
            return jsonify({'error': 'Missing scan_id or comment parameter'}), 400
        
        scan_id = data['scan_id']
        comment_text = data['comment'].strip()
        
        if not comment_text:
            return jsonify({'error': 'Comment cannot be empty'}), 400
        
        # Find the scan belonging to the current user
        scan = Scan.query.filter_by(id=scan_id, user_id=current_user.id).first()
        if not scan:
            return jsonify({'error': 'Scan not found or access denied'}), 404
        
        # Update the scan's comment
        scan.comments = comment_text
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Comment saved successfully'
        })
        
    except Exception as e:
        print(f"Error saving comment: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to save comment'}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port, debug=True)
