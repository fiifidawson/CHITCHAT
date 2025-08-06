import json
import os
from typing import List, Dict, Optional

class UniqueBooleanCombinationsGenerator:
    """
    Generates pre-defined unique boolean combinations for research paper searches
    based on research categories and predefined key combinations from boolean_combinations.json
    """
    
    def __init__(self, boolean_combinations_file='../../data/boolean_combinations.json'):
        self.boolean_combinations_file = boolean_combinations_file
        self.boolean_combinations_data = self._load_boolean_combinations()
        
        # Pre-defined combinations for each research category
        # Each list contains keys that correspond to "WORD" values in boolean_combinations.json
        self.predefined_combinations = {
            "Broad Foundational Search": [
                "Foundation model",
                "Data Curation & Processing", 
                "Data Collection Methods",
                "Rights & Data Protection Frameworks",
                "Applications & Domains"
            ],
            
            "Humanitarian & Social Impact Search": [
                "Humanitarian & Crisis Response",
                "Foundation model",
                "Bias",
                "Fairness",
                "Social Impact Assessment"
            ],
            
            "Inclusion & Representation Search": [
                "Foundation model",
                "Bias",
                "Fairness", 
                "Inclusion & Diversity",
                "Representation",
                "Cultural Sensitivity"
            ],
            
            "Harm Reduction & Safety Search": [
                "Foundation model",
                "Harm Mitigation",
                "Safety Measures",
                "Risk Assessment",
                "Bias",
                "Fairness"
            ],
            
            "Control, Consent & Personal Data Rights": [
                "Foundation model",
                "Rights & Data Protection Frameworks",
                "Data Control",
                "Consent Mechanisms",
                "Privacy Protection"
            ],
            
            "Consent, Agency & Participatory AI": [
                "Foundation model", 
                "Consent Mechanisms",
                "User Agency",
                "Participatory Design",
                "Human-AI Interaction"
            ],
            
            "Environmental & Infrastructural Cost": [
                "Foundation model",
                "Environmental Impact",
                "Computational Resources",
                "Energy Consumption",
                "Sustainability"
            ],
            
            "Post-Deployment Monitoring & Redress": [
                "Foundation model",
                "Monitoring Systems",
                "Performance Evaluation",
                "Redress Mechanisms",
                "Accountability"
            ]
        }
    
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
    
    def _find_boolean_combination_by_key(self, key: str) -> Optional[str]:
        """Find the boolean combination for a given key (WORD)"""
        if not self.boolean_combinations_data:
            return None
            
        for item in self.boolean_combinations_data:
            if item.get('WORD', '').strip() == key.strip():
                return item.get('boolean_combination', '')
        return None
    
    def _generate_combination_for_category(self, category: str, keys: List[str]) -> Optional[Dict]:
        """Generate a unique boolean combination for a specific category"""
        boolean_parts = []
        found_keys = []
        missing_keys = []
        
        for key in keys:
            boolean_combo = self._find_boolean_combination_by_key(key)
            if boolean_combo:
                boolean_parts.append(boolean_combo)
                found_keys.append(key)
            else:
                missing_keys.append(key)
                print(f"Warning: Key '{key}' not found in boolean_combinations.json")
        
        if not boolean_parts:
            print(f"Error: No valid boolean combinations found for category '{category}'")
            return None
        
        # Join with AND operators
        if len(boolean_parts) == 1:
            unique_combination = boolean_parts[0]
        else:
            unique_combination = " AND ".join(boolean_parts)
        
        return {
            "Combination_title": category,
            "boolean_combination": unique_combination,
            "selected_keys": found_keys,
            "missing_keys": missing_keys,
            "key_count": len(found_keys)
        }
    
    def generate_all_unique_combinations(self) -> List[Dict]:
        """Generate unique combinations for all predefined research categories"""
        if not self.boolean_combinations_data:
            print("Error: No boolean combinations data loaded")
            return []
        
        unique_combinations = []
        
        print("Generating unique boolean combinations...")
        print("=" * 50)
        
        for category, keys in self.predefined_combinations.items():
            print(f"\nProcessing: {category}")
            print(f"Keys: {', '.join(keys)}")
            
            combination = self._generate_combination_for_category(category, keys)
            
            if combination:
                unique_combinations.append(combination)
                print(f"✓ Generated combination with {combination['key_count']} keys")
                
                if combination['missing_keys']:
                    print(f"⚠ Missing keys: {', '.join(combination['missing_keys'])}")
            else:
                print(f"✗ Failed to generate combination")
        
        print(f"\nGenerated {len(unique_combinations)} unique combinations")
        return unique_combinations
    
    def save_unique_combinations(self, combinations: List[Dict], output_file='../../data/unique_boolean_combinations.json'):
        """Save unique combinations to JSON file"""
        try:
            # Clean the combinations for final output (remove internal tracking)
            cleaned_combinations = []
            for combo in combinations:
                cleaned_combo = {
                    "Combination_title": combo["Combination_title"],
                    "boolean_combination": combo["boolean_combination"]
                }
                cleaned_combinations.append(cleaned_combo)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(cleaned_combinations, f, indent=4, ensure_ascii=False)
            print(f"\n✓ Successfully saved to {output_file}")
            return True
        except Exception as e:
            print(f"✗ Error saving file: {str(e)}")
            return False
    
    def display_available_keys(self):
        """Display all available keys from boolean_combinations.json"""
        if not self.boolean_combinations_data:
            print("No boolean combinations data available.")
            return
        
        print("\nAvailable keys in Boolean_combinations.json:")
        print("-" * 50)
        for i, item in enumerate(self.boolean_combinations_data, 1):
            print(f"{i:2d}. {item.get('WORD', 'N/A')}")
    
    def update_predefined_combination(self, category: str, new_keys: List[str]):
        """Update the predefined combination for a specific category"""
        if category in self.predefined_combinations:
            self.predefined_combinations[category] = new_keys
            print(f"Updated predefined combination for '{category}'")
        else:
            print(f"Category '{category}' not found in predefined combinations")
    
    def display_predefined_combinations(self):
        """Display all predefined combinations"""
        print("\nPredefined Combinations:")
        print("=" * 60)
        for category, keys in self.predefined_combinations.items():
            print(f"\n{category}:")
            for i, key in enumerate(keys, 1):
                print(f"  {i}. {key}")

def generate_unique_boolean_combinations(input_file='../../data/boolean_combinations.json', output_file='../../output/unique_boolean_combinations.json'):
    """
    Generate unique boolean combinations and save to JSON file
    
    Args:
        input_file (str): Path to the boolean combinations JSON file
        output_file (str): Path to the output unique combinations JSON file
    
    Returns:
        bool: True if successful, False otherwise
    """
    generator = UniqueBooleanCombinationsGenerator(input_file)
    
    if not generator.boolean_combinations_data:
        print(f"Error: Cannot proceed without {input_file}")
        return False
    
    # Generate all combinations
    combinations = generator.generate_all_unique_combinations()
    
    if combinations:
        # Save to file
        success = generator.save_unique_combinations(combinations, output_file)
        return success
    else:
        print("Error: No combinations generated")
        return False

def main():
    """Main function - simply generate the JSON file"""
    success = generate_unique_boolean_combinations()
    if success:
        print("✓ Unique boolean combinations generated successfully!")
    else:
        print("✗ Failed to generate unique boolean combinations")

if __name__ == "__main__":
    main()