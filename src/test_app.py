from flask import Flask, render_template_string
import os

app = Flask(__name__)

@app.route('/')
def home():
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Food Label Scanner - Test</title>
    </head>
    <body>
        <h1>Food Label Scanner is Running!</h1>
        <p>✅ Flask app is working</p>
        <p>Environment variables:</p>
        <ul>
            <li>CLAUDE_SONNET_API_KEY: {{ "Set" if claude_key else "Missing" }}</li>
            <li>AZURE_FORM_RECOGNIZER_ENDPOINT: {{ "Set" if form_recognizer_endpoint else "Missing" }}</li>
            <li>AZURE_FORM_RECOGNIZER_KEY: {{ "Set" if form_recognizer_key else "Missing" }}</li>
            <li>DATABASE_URL: {{ "Set" if database_url else "Missing" }}</li>
            <li>SECRET_KEY: {{ "Set" if secret_key else "Missing" }}</li>
        </ul>
    </body>
    </html>
    ''', 
    claude_key=bool(os.getenv('CLAUDE_SONNET_API_KEY')),
    form_recognizer_endpoint=bool(os.getenv('AZURE_FORM_RECOGNIZER_ENDPOINT')),
    form_recognizer_key=bool(os.getenv('AZURE_FORM_RECOGNIZER_KEY')),
    database_url=bool(os.getenv('DATABASE_URL')),
    secret_key=bool(os.getenv('SECRET_KEY'))
    )

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port, debug=True) 