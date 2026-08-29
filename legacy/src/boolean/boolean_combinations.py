import json

def generate_boolean_combinations(input_file='../../data/structure.json', output_file='../../data/boolean_combinations.json'):
    """
    Reads structure.json and generates Boolean_combinations.json with boolean search combinations.
    
    Args:
        input_file (str): Path to the input JSON file containing words and synonyms
        output_file (str): Path to the output JSON file for boolean combinations
    """
    
    try:
        # Read the input JSON file
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Generate boolean combinations
        boolean_combinations = []
        
        for item in data:
            word = item.get("WORD", "")
            synonyms_str = item.get("SYNONYMS AND NEAR SYNONYMS", "")
            
            if not word or not synonyms_str:
                continue
            
            # Split synonyms by comma and clean up whitespace
            synonyms = [synonym.strip() for synonym in synonyms_str.split(',')]
            
            # Create the main word list (include the original word + synonyms)
            all_terms = [word] + synonyms
            
            # Remove empty strings and duplicates while preserving order
            unique_terms = []
            seen = set()
            for term in all_terms:
                if term and term not in seen:
                    unique_terms.append(f'"{term}"')
                    seen.add(term)
            
            # Create boolean combination with OR operators
            if unique_terms:
                boolean_combination = f"({' OR '.join(unique_terms)})"
                
                boolean_combinations.append({
                    "WORD": word,
                    "boolean_combination": boolean_combination
                })
        
        # Write to output file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(boolean_combinations, f, indent=4, ensure_ascii=False)
        
        print(f"Successfully generated {output_file} with {len(boolean_combinations)} boolean combinations.")
        return boolean_combinations
        
    except FileNotFoundError:
        print(f"Error: {input_file} not found.")
        return None
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in {input_file}.")
        return None
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None

# Example usage
if __name__ == "__main__":
    # Generate the boolean combinations
    result = generate_boolean_combinations()
    
    # Optional: Print first few results for verification
    if result:
        print("\nFirst few boolean combinations:")
        for i, combo in enumerate(result[:3]):
            print(f"{i+1}. {combo['WORD']}: {combo['boolean_combination']}")