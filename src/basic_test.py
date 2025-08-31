import sys
import os
from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    info = f"""
    <h1>Python Test - Azure App Service</h1>
    <p>✅ Python version: {sys.version}</p>
    <p>✅ Current directory: {os.getcwd()}</p>
    <p>✅ Flask is working!</p>
    <h2>Environment Variables:</h2>
    <ul>
    """
    
    for key, value in os.environ.items():
        if 'PYTHON' in key or 'PATH' in key or 'SECRET' in key:
            info += f"<li><strong>{key}:</strong> {value[:50]}{'...' if len(value) > 50 else ''}</li>"
    
    info += "</ul>"
    return info

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port, debug=True) 