#!/usr/bin/env python3
"""
Test script for Brevo email functionality
"""
import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.append('src')

# Load environment variables
load_dotenv()

# Import the email function
from app import send_email_brevo

def test_brevo_email():
    """Test the Brevo email functionality"""
    print("Testing Brevo email functionality...")
    
    # Test email details - try a different email
    test_email = "test@example.com"  # Change this to a different email you have access to
    subject = "Test Email - Food Label Scanner"
    
    html_content = """
    <html>
    <body>
        <h2>Test Email</h2>
        <p>This is a test email from the Food Label Scanner application.</p>
        <p>If you receive this email, the Brevo integration is working correctly!</p>
        <br>
        <p>Best regards,<br>Food Label Scanner Team</p>
    </body>
    </html>
    """
    
    text_content = """Test Email

This is a test email from the Food Label Scanner application.

If you receive this email, the Brevo integration is working correctly!

Best regards,
Food Label Scanner Team"""
    
    # Send test email
    print(f"Sending test email to: {test_email}")
    result = send_email_brevo(test_email, subject, html_content, text_content)
    
    if result:
        print("✅ Email sent successfully!")
    else:
        print("❌ Email sending failed!")
    
    return result

if __name__ == "__main__":
    test_brevo_email() 