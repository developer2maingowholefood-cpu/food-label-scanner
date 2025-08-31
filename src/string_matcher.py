import re


class StringMatcher:
    def __init__(self, threshold=0.85):
        self.threshold = threshold
    
    def normalize_text(self, text: str) -> str:
        """Normalize text for consistent matching"""
        # Convert to uppercase and remove extra spaces
        text = str(text).upper().strip()
        # Remove parenthetical content
        text = re.sub(r'\([^)]*\)', '', text)
        # Standardize whitespace
        text = ' '.join(text.split())
        return text