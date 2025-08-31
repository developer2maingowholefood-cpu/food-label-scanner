import pandas as pd
import re
from typing import Tuple, Set, List


class NoGoChecker:
    def __init__(self, csv_path: str):
        """Initialize NoGoChecker with path to CSV file"""
        # Read the CSV file
        self.nogo_df = pd.read_csv(csv_path)
        self.ingredient_column = self.nogo_df.columns[0]
        self.category_column = self.nogo_df.columns[1] if len(
            self.nogo_df.columns) > 1 else None

        # Create normalized ingredient lookup
        self.nogo_ingredients = {}
        for _, row in self.nogo_df.iterrows():
            ingredient = str(row[self.ingredient_column]).strip()
            category = row[self.category_column] if self.category_column else 'Unknown'
            normalized = self._normalize_text(ingredient)
            self.nogo_ingredients[normalized] = {
                'original': ingredient,
                'category': category
            }

    def _normalize_text(self, text: str) -> str:
        """Normalize text for consistent matching"""
        # Convert to uppercase and remove extra spaces
        text = str(text).upper().strip()
        # Remove parenthetical content
        text = re.sub(r'\([^)]*\)', '', text)
        # Standardize whitespace
        text = ' '.join(text.split())
        return text

    def check_ingredients(self, ingredients_text: str) -> Tuple[bool, Set[str], List[str]]:
        """
        Check if the raw text contains any NoGo ingredients using comma-separated exact tokens.
        Returns: (is_nogo, found_terms, categories)
        """
        found_terms = set()
        categories = set()

        # Split the input text by commas into tokens
        tokens = [token.strip() for token in ingredients_text.split(',')]
        for token in tokens:
            normalized_token = self._normalize_text(token)
            # Only flag if the entire token exactly matches a NoGo ingredient
            if normalized_token in self.nogo_ingredients:
                info = self.nogo_ingredients[normalized_token]
                found_terms.add(info['original'])
                categories.add(info['category'])
        return bool(found_terms), found_terms, list(categories)

    def debug_check(self, ingredients_text: str) -> dict:
        """
        For debugging: split the text into tokens, normalize them, and show any exact matches.
        """
        tokens = [token.strip() for token in ingredients_text.split(',')]
        normalized_tokens = [self._normalize_text(token) for token in tokens]
        matches = []
        for token, normalized_token in zip(tokens, normalized_tokens):
            if normalized_token in self.nogo_ingredients:
                info = self.nogo_ingredients[normalized_token]
                matches.append({
                    'token': token,
                    'normalized': normalized_token,
                    'ingredient': info['original'],
                    'category': info['category']
                })
        return {
            'original_text': ingredients_text,
            'tokens': tokens,
            'normalized_tokens': normalized_tokens,
            'matches': matches,
            'total_ingredients_checked': len(self.nogo_ingredients)
        }
