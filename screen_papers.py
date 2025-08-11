import os
import sys
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime
from tqdm import tqdm
import re

from openai import OpenAI
from pydantic import BaseModel, Field


# Simplified models focusing on raw assessments
class PublicationQuality(BaseModel):
    venue_name: str = Field(description="Name of the publication venue")
    is_top_tier_venue: bool = Field(description="Published in top-tier conference or Q1/Q2 journal")
    citation_count: int = Field(description="Number of citations")
    is_recent_promising: bool = Field(description="Less than 1 year old with promising indicators (awards, policy citations)")
    full_text_english: bool = Field(description="Full text accessible and in English")


class TechnicalScope(BaseModel):
    addresses_llm_data_collection: bool = Field(description="Addresses LLM training data collection")
    addresses_text_corpus_creation: bool = Field(description="Addresses text corpus creation")
    addresses_web_scraping_nlp: bool = Field(description="Addresses web scraping for NLP datasets")
    addresses_multilingual_compilation: bool = Field(description="Addresses multilingual dataset compilation")


class HumanitarianPrinciples(BaseModel):
    humanity_score: int = Field(description="Score for preventing harm (0-3)", ge=0, le=3)
    impartiality_score: int = Field(description="Score for fair representation (0-3)", ge=0, le=3)
    independence_score: int = Field(description="Score for autonomy from biasing influences (0-3)", ge=0, le=3)
    neutrality_score: int = Field(description="Score for avoiding discriminatory data collection (0-3)", ge=0, le=3)


class EthicalFlags(BaseModel):
    focuses_only_on_performance: bool = Field(description="Focuses exclusively on model performance without ethics discussion")
    disregards_ethical_principles: bool = Field(description="Clearly disregards consent or privacy")
    missing_ethical_approval: bool = Field(description="Missing IRB approval when dealing with vulnerable groups")
    violates_humanitarian_principles: bool = Field(description="Uses discriminatory algorithms or has military intent")


class MethodologyContributions(BaseModel):
    novel_methodology: bool = Field(description="Provides novel data collection methodology")
    systematic_evaluation: bool = Field(description="Offers systematic evaluation or comparative analysis")
    reproducible_implementation: bool = Field(description="Includes reproducible implementation details")


class EthicalContributions(BaseModel):
    explicit_framework: bool = Field(description="Includes explicit ethical framework or principles")
    empirical_bias_analysis: bool = Field(description="Contains empirical analysis of bias in data")
    harm_mitigation_strategies: bool = Field(description="Proposes concrete harm mitigation strategies")
    policy_recommendations: bool = Field(description="Provides policy or data governance recommendations")
    acknowledges_tensions: bool = Field(description="Acknowledges ethical tensions and trade-offs")


class PriorityLevel(str, Enum):
    HIGH = "HIGH PRIORITY"
    MEDIUM = "MEDIUM PRIORITY"
    LOW = "LOW PRIORITY"
    EXCLUDE = "EXCLUDE"


class PaperScreening(BaseModel):
    # Basic information
    paper_title: str = Field(description="Title of the paper")
    
    # Phase 1: Raw assessments
    publication_quality: PublicationQuality
    technical_scope: TechnicalScope
    
    # Phase 2: Raw assessments
    ethical_flags: EthicalFlags
    humanitarian_principles: HumanitarianPrinciples
    
    # Phase 3: Raw assessments
    methodology_contributions: MethodologyContributions
    ethical_contributions: EthicalContributions
    
    # Final priority assignment by LLM
    priority_level: PriorityLevel = Field(description="Final priority level based on all assessments")

def load_papers_from_json(json_path: str) -> List[Dict[str, Any]]:
    """Load papers from a JSON file."""
    try:
        with open(json_path, 'r', encoding='utf-8') as file:
            papers = json.load(file)
            print(f"Loaded {len(papers)} papers from {json_path}")
            return papers
    except Exception as e:
        print(f"Error reading JSON file: {e}")
        return []

def create_unique_id(title: str) -> str:
    """Create a unique identifier from the title."""
    # Convert to lowercase, remove non-alphanumeric characters
    unique_id = re.sub(r'[^a-z0-9]', '', title.lower())
    return unique_id


def load_prompt(prompt_path: str) -> str:
    """Load the prompt from a text file."""
    try:
        with open(prompt_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        print(f"Error reading prompt file: {e}")
        return ""


def screen_paper(client: OpenAI, prompt_text: str, paper: Dict[str, Any]) -> PaperScreening:
    """Screen a paper using OpenAI's API with structured outputs."""
    
    # Prepare paper content
    paper_content = f"""
PAPER TITLE: {paper.get('title', 'N/A')}

ABSTRACT:
{paper.get('abstract', 'No abstract available')}

FULL TEXT:
{paper.get('extracted_text', 'No full text available')}
"""
    
    # Truncate paper content to first 60000 characters (money and context length reseaons)
    truncated_paper_content = paper_content[:60000]

    # Combine the prompt with the paper text
    full_prompt = f"{prompt_text}\n\n---PAPER CONTENT BEGINS---\n{truncated_paper_content}\n---PAPER CONTENT ENDS---"
    
    try:
        completion = client.beta.chat.completions.parse(
            model="gpt-5-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert research paper screener. Provide objective assessments based only on the content provided."
                },
                {
                    "role": "user",
                    "content": full_prompt
                }
            ],
            response_format=PaperScreening
            # temperature=0.3
        )
        
        return completion.choices[0].message.parsed
    
    except Exception as e:
        print(f"Error calling OpenAI API for paper '{paper.get('title', 'Unknown')}': {e}")
        raise


def append_screening_result(screening: PaperScreening, paper: Dict, output_file: str):
    """Append a single screening result to the JSON file."""
        
    result = {
        "title": screening.paper_title,
        "original_metadata": {
            "authors": paper.get('authors', []),
            "year": paper.get('year', 'N/A'),
            "url": paper.get('url', 'N/A')
        },
        "screening_results": screening.model_dump(),
        "final_priority": screening.priority_level.value
    }

    # Simply append as a new line in JSONL format
    with open(output_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(result) + '\n')

def main():
    # Check command line arguments
    if len(sys.argv) != 3:
        print("Usage: python screen_papers.py <prompt_file.txt> <papers.json>")
        sys.exit(1)
    
    prompt_file = sys.argv[1]
    json_file = sys.argv[2]
    
    # Check if files exist
    if not os.path.exists(prompt_file):
        print(f"Error: Prompt file '{prompt_file}' not found.")
        sys.exit(1)
    
    if not os.path.exists(json_file):
        print(f"Error: JSON file '{json_file}' not found.")
        sys.exit(1)
    
    # Get API key from environment variable
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set.")
        sys.exit(1)
    
    # Initialize OpenAI client
    client = OpenAI(api_key=api_key)
    
    # Load prompt and papers
    print("Loading prompt...")
    prompt_text = load_prompt(prompt_file)
    
    print("Loading papers from JSON...")
    papers = load_papers_from_json(json_file)
    
    if not papers:
        print("Error: No papers found in JSON file.")
        sys.exit(1)
    
    # Create output file with timestamp
    output_file = f"output/screening_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
    print(f"Results will be saved to: {output_file}")
    
    # Track processed papers to avoid duplicates
    processed_ids = set()
    
    # Screen each paper and save immediately
    successful_count = 0
    failed_count = 0
    year_count = 0
    extext_count = 0
    duplicate_count = 0
    
    print(f"Start screening {len(papers)} papers...")
    for i, paper in tqdm(enumerate(papers, 1)):

        # create unique identifier
        title = paper.get('title', '')
        unique_id = create_unique_id(title)
        
        # Check publication year
        year = paper.get('year', 0)
        try:
            year = int(year) if year else 0
        except (ValueError, TypeError):
            year = 0
        
        if year < 2020:
            # print(f"  ⊘ Skipping paper (year {year} < 2020): {paper.get('title', 'Unknown')[:50]}...")
            year_count += 1
            continue
        
        # Check extracted text length
        extracted_text = paper.get('extracted_text') or ''
        if len(extracted_text) < 500:
            # print(f"  ⊘ Skipping paper (text too short: {len(extracted_text)} chars): {paper.get('title', 'Unknown')[:50]}...")
            extext_count += 1
            continue
        
        # Check for duplicates
        if unique_id in processed_ids:
            # print(f"  ⊘ Skipping duplicate: {title[:50]}...")
            duplicate_count += 1
            continue
        
        processed_ids.add(unique_id)
        
        try:
            screening = screen_paper(client, prompt_text, paper)
            
            # Save result immediately
            append_screening_result(screening, paper, output_file)
            successful_count += 1
                        
        except Exception as e:
            print(f"  ✗ Failed to screen: {e}")
            failed_count += 1
            continue
    
    # Print final summary
    print("\n" + "="*50)
    print("SCREENING COMPLETE")
    print("="*50)
    print(f"Successfully screened: {successful_count}/{len(papers)} papers")
    if failed_count > 0:
        print(f"Failed: {failed_count} papers")
    if year_count > 0:
        print(f"Skipped (year filters): {year_count} papers")
    if year_count > 0:
        print(f"Skipped (text filters): {extext_count} papers")
    if duplicate_count > 0:
        print(f"Skipped (duplicates): {duplicate_count} papers")
    print(f"\nAll results saved to: {output_file}")


if __name__ == "__main__":
    main()