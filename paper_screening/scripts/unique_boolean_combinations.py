import json
import os
from typing import List, Dict, Optional

class UniqueBooleanCombinationsGenerator:
    """
    Generates unique boolean combinations for research paper searches based on 
    research categories and selected terms from boolean_combinations.json
    """
    
    def __init__(self, boolean_combinations_file='../../data/boolean_combinations.json'):
        self.boolean_combinations_file = boolean_combinations_file
        self.research_categories = [
            "Broad Foundational Search",
            "Humanitarian & Social Impact Search", 
            "Inclusion & Representation Search",
            "Harm Reduction & Safety Search",
            "Control, Consent & Personal Data Rights",
            "Consent, Agency & Participatory AI",
            "Environmental & Infrastructural Cost",
            "Post-Deployment Monitoring & Redress"
        ]
        self.boolean_combinations_data = self._load_boolean_combinations()
    
    def _load_boolean_combinations(self) -> Optional[List[Dict]]:
        """Load the boolean combinations from JSON file"""
        try:
            with open(self.boolean_combinations_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: {self.boolean_combinations_file} not found.")
            return None
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON format in {self.boolean_combinations_file}.")
            return None
    
    def display_available_terms(self):
        """Display all available terms from boolean_combinations.json"""
        if not self.boolean_combinations_data:
            print("No boolean combinations data available.")
            return
        
        print("\nAvailable terms from Boolean_combinations.json:")
        print("-" * 50)
        for i, item in enumerate(self.boolean_combinations_data, 1):
            print(f"{i:2d}. {item['WORD']}")
    
    def display_research_categories(self):
        """Display available research categories"""
        print("\nAvailable Research Categories:")
        print("-" * 40)
        for i, category in enumerate(self.research_categories, 1):
            print(f"{i}. {category}")
    
    def get_user_selection(self) -> Optional[Dict]:
        """Interactive function to get user selections"""
        print("=== Unique Boolean Combinations Generator ===\n")
        
        # Select research category
        self.display_research_categories()
        try:
            category_choice = int(input(f"\nSelect research category (1-{len(self.research_categories)}): ")) - 1
            if category_choice < 0 or category_choice >= len(self.research_categories):
                print("Invalid category selection.")
                return None
            selected_category = self.research_categories[category_choice]
        except ValueError:
            print("Invalid input. Please enter a number.")
            return None
        
        # Select terms
        self.display_available_terms()
        print(f"\nSelected Category: {selected_category}")
        print("Select multiple terms by entering their numbers separated by commas (e.g., 1,3,5):")
        
        try:
            term_choices = input("Enter term numbers: ").strip()
            term_indices = [int(x.strip()) - 1 for x in term_choices.split(',')]
            
            selected_terms = []
            for idx in term_indices:
                if 0 <= idx < len(self.boolean_combinations_data):
                    selected_terms.append(self.boolean_combinations_data[idx])
                else:
                    print(f"Warning: Invalid term number {idx + 1} ignored.")
            
            if not selected_terms:
                print("No valid terms selected.")
                return None
                
        except ValueError:
            print("Invalid input format. Please use numbers separated by commas.")
            return None
        
        return {
            "research_category": selected_category,
            "selected_terms": selected_terms
        }
    
    def generate_unique_combination(self, research_category: str, selected_terms: List[Dict]) -> Dict:
        """Generate a unique boolean combination"""
        # Extract boolean combinations from selected terms
        boolean_parts = []
        selected_words = []
        
        for term in selected_terms:
            boolean_parts.append(term['boolean_combination'])
            selected_words.append(term['WORD'])
        
        # Join multiple boolean combinations with AND
        if len(boolean_parts) == 1:
            unique_combination = boolean_parts[0]
        else:
            unique_combination = " AND ".join(boolean_parts)
        
        return {
            "research_category": research_category,
            "selected_terms": selected_words,
            "unique_boolean_combination": unique_combination,
            "term_count": len(selected_terms)
        }
    
    def save_unique_combinations(self, combinations: List[Dict], output_file='../../data/unique_boolean_combinations.json'):
        """Save unique combinations to JSON file"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(combinations, f, indent=4, ensure_ascii=False)
            print(f"\nSuccessfully saved to {output_file}")
        except Exception as e:
            print(f"Error saving file: {str(e)}")
    
    def create_combination_programmatically(self, research_category: str, term_words: List[str]) -> Optional[Dict]:
        """Create combination programmatically without user interaction"""
        if not self.boolean_combinations_data:
            return None
        
        # Find selected terms by WORD
        selected_terms = []
        for word in term_words:
            for item in self.boolean_combinations_data:
                if item['WORD'].lower() == word.lower():
                    selected_terms.append(item)
                    break
            else:
                print(f"Warning: Term '{word}' not found in boolean combinations.")
        
        if not selected_terms:
            print("No valid terms found.")
            return None
        
        return self.generate_unique_combination(research_category, selected_terms)

def interactive_mode():
    """Run the generator in interactive mode"""
    generator = UniqueBooleanCombinationsGenerator()
    
    if not generator.boolean_combinations_data:
        return
    
    combinations = []
    
    while True:
        selection = generator.get_user_selection()
        if not selection:
            continue
        
        # Generate unique combination
        unique_combo = generator.generate_unique_combination(
            selection['research_category'], 
            selection['selected_terms']
        )
        
        combinations.append(unique_combo)
        
        # Display the generated combination
        print(f"\nGenerated Combination:")
        print(f"Category: {unique_combo['research_category']}")
        print(f"Terms: {', '.join(unique_combo['selected_terms'])}")
        print(f"Boolean: {unique_combo['unique_boolean_combination']}")
        
        # Ask if user wants to create another combination
        another = input("\nCreate another combination? (y/n): ").lower().strip()
        if another not in ['y', 'yes']:
            break
    
    # Save all combinations
    if combinations:
        generator.save_unique_combinations(combinations)
        print(f"\nTotal combinations created: {len(combinations)}")

def programmatic_example():
    """Example of programmatic usage"""
    generator = UniqueBooleanCombinationsGenerator()
    
    # Example: Create combination programmatically
    combination = generator.create_combination_programmatically(
        research_category="Harm Reduction & Safety Search",
        term_words=["Foundation model", "Bias"]  # Replace with actual terms from your data
    )
    
    if combination:
        print("Programmatically generated combination:")
        print(json.dumps(combination, indent=2))
        generator.save_unique_combinations([combination])

if __name__ == "__main__":
    print("Choose mode:")
    print("1. Interactive mode")
    print("2. Programmatic example")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        interactive_mode()
    elif choice == "2":
        programmatic_example()
    else:
        print("Invalid choice. Running interactive mode by default.")
        interactive_mode()