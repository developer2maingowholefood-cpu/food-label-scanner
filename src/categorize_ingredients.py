import pandas as pd
import re
import os
from typing import Dict, List
from datetime import datetime
from string_matcher import StringMatcher


class IngredientCategorizer:
    def __init__(self):
        self.matcher = StringMatcher(threshold=0.85)

        # Define category patterns
        self.category_patterns = {
            'Juices': r'.*\sjuice$',
            'Sweeteners': r'.*(sugar|syrup|honey|nectar|dextrose|fructose|glucose|maltose|sucrose|stevia|allulose)$',
            'Starches': r'.*(starch|flour|meal)$',
            'Proteins': r'.*(protein|isolate|concentrate)$',
            'Oils': r'.*(oil|fat)$',
            'Additives': r'.*(acid|sulfite|sulfate|chloride|benzoate|sorbate|nitrite|carbonate|citrate|phosphate)$',
            'Flavors': r'.*(flavor|extract)$',
            'Enzymes': r'.*(enzyme|protease|amylase|lipase)$',
            'Preservatives': r'.*(BHA|BHT|TBHQ|preservative)$',
            'Gums': r'.*(gum|carrageenan|pectin)$',
            'Vitamins': r'.*(vitamin|tocopherol)$',
            'Grains': r'.*(rice|wheat|barley|corn|oat|rye|spelt)$',
            'Colors': r'.*(color|annatto|caramel)$'
        }

    def categorize_ingredient(self, ingredient: str) -> str:
        """Categorize a single ingredient based on patterns"""
        normalized = self.matcher.normalize_text(ingredient)

        # Check each pattern
        for category, pattern in self.category_patterns.items():
            if re.search(pattern, normalized, re.IGNORECASE):
                return category

        return 'General'

    def process_ingredients(self, input_file: str, output_file: str):
        """Process the ingredients list and create categorized CSV"""
        print(f"\nStarting ingredient categorization at {datetime.now()}")
        print(f"Reading ingredients from {input_file}...")

        # Read ingredients
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                ingredients = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            raise FileNotFoundError(f"Input file not found: {input_file}")

        # Remove header if it exists
        if ingredients[0].lower() == 'nogo ingredients':
            ingredients = ingredients[1:]

        # Process ingredients
        data = []
        for ingredient in ingredients:
            if ingredient:  # Skip empty lines
                normalized = self.matcher.normalize_text(ingredient)
                category = self.categorize_ingredient(ingredient)

                data.append({
                    'ingredient': ingredient,
                    'normalized': normalized,
                    'category': category
                })

        # Create DataFrame
        df = pd.DataFrame(data)
        df = df.sort_values(['category', 'ingredient'])

        # Save files
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        # Save debug version
        debug_file = output_file.replace('.csv', '_debug.csv')
        df.to_csv(debug_file, index=False)

        # Save production version
        df[['ingredient', 'category']].to_csv(output_file, index=False)

        # Print summary
        print("\n=== Processing Summary ===")
        print(f"Total ingredients processed: {len(df)}")

        print("\nIngredients by category:")
        for category in sorted(df['category'].unique()):
            count = len(df[df['category'] == category])
            print(f"\n{category}: {count} ingredients")
            examples = df[df['category'] ==
                          category]['ingredient'].head(3).tolist()
            print(f"  Examples: {', '.join(examples)}")

            # Show normalized version of first example
            if examples:
                normalized = df[df['ingredient'] ==
                                examples[0]]['normalized'].iloc[0]
                print(f"  Normalized example: {normalized}")

        # Print General category ingredients
        general = df[df['category'] == 'General']
        if len(general) > 0:
            print("\n=== Uncategorized Ingredients ===")
            print(f"Total: {len(general)}")
            for _, row in general.head(10).iterrows():
                print(f"  - {row['ingredient']}")
            if len(general) > 10:
                print(f"  ... and {len(general) - 10} more")

        print(f"\nOutput saved to: {output_file}")
        print(f"Debug version saved to: {debug_file}")
        print(f"Processing completed at {datetime.now()}")


def main():
    """Main execution function"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(script_dir, 'latest_nogo_ingredients_July302025.csv')
    output_file = os.path.join(script_dir, 'nogo_ingredients.csv')

    categorizer = IngredientCategorizer()

    try:
        categorizer.process_ingredients(input_file, output_file)
        print("\nProcessing completed successfully!")

    except Exception as e:
        print(f"\nError during processing: {str(e)}")
        raise


if __name__ == "__main__":
    main()
