import os
import sys
import json
from pathlib import Path
from typing import List, Optional, Literal
from enum import Enum

import PyPDF2
from openai import OpenAI
from pydantic import BaseModel, Field


# Define the structured output models based on the screening framework
class PublicationQuality(BaseModel):
    is_top_tier_venue: bool = Field(description="Published in top-tier conference or Q1/Q2 journal")
    published_2020_or_later: bool = Field(description="Published in 2020 or later")
    sufficient_citations: bool = Field(description="10+ citations OR less than 1 year old with promising indicators")
    full_text_english: bool = Field(description="Full text accessible and in English")
    passes_phase1: bool = Field(description="Meets all Phase 1 criteria")


class TechnicalScope(BaseModel):
    addresses_llm_data_collection: bool = Field(description="Addresses LLM training data collection")
    addresses_text_corpus_creation: bool = Field(description="Addresses text corpus creation")
    addresses_web_scraping_nlp: bool = Field(description="Addresses web scraping for NLP datasets")
    addresses_multilingual_compilation: bool = Field(description="Addresses multilingual dataset compilation")
    passes_technical_scope: bool = Field(description="Addresses at least one technical scope area")


class EthicalKnockout(BaseModel):
    focuses_only_on_performance: bool = Field(description="Focuses exclusively on model performance without ethics discussion")
    disregards_ethical_principles: bool = Field(description="Clearly disregards consent or privacy")
    missing_ethical_approval: bool = Field(description="Missing IRB approval when dealing with vulnerable groups")
    violates_humanitarian_principles: bool = Field(description="Uses discriminatory algorithms or has military intent")
    humanitarian_score: int = Field(description="Score out of 12 on humanitarian principles scale", ge=0, le=12)
    fails_phase2: bool = Field(description="Fails any Phase 2 criteria (should be excluded)")


class MethodologyContribution(BaseModel):
    novel_methodology: bool = Field(description="Provides novel data collection methodology")
    systematic_evaluation: bool = Field(description="Offers systematic evaluation or comparative analysis")
    reproducible_implementation: bool = Field(description="Includes reproducible implementation details")
    has_high_value_methodology: bool = Field(description="Has at least one high-value methodology contribution")


class EthicalAnalysis(BaseModel):
    explicit_framework: bool = Field(description="Includes explicit ethical framework or principles")
    empirical_bias_analysis: bool = Field(description="Contains empirical analysis of bias in data")
    harm_mitigation_strategies: bool = Field(description="Proposes concrete harm mitigation strategies")
    policy_recommendations: bool = Field(description="Provides policy or data governance recommendations")
    acknowledges_tensions: bool = Field(description="Acknowledges ethical tensions and trade-offs")
    has_high_value_ethics: bool = Field(description="Has at least one high-value ethical contribution")


class PriorityLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    EXCLUDE = "exclude"


class PaperAnalysis(BaseModel):
    # Basic information
    paper_title: str = Field(description="Title of the paper")
    summary: str = Field(description="Brief summary of the paper's main contribution")
    
    # Phase 1: Initial Filter
    publication_quality: PublicationQuality
    technical_scope: TechnicalScope
    
    # Phase 2: Ethical & Humanitarian Knockout
    ethical_knockout: EthicalKnockout
    
    # Phase 3: In-Depth Assessment
    methodology_contribution: MethodologyContribution
    ethical_analysis: EthicalAnalysis
    
    # Phase 4: Final Decision
    priority_level: PriorityLevel = Field(description="Final priority level based on all phases")
    recommendation: str = Field(description="Detailed recommendation for action")
    key_insights: List[str] = Field(description="Key insights relevant to LLM data collection")


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text content from a PDF file."""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text()
            return text
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return ""


def load_prompt(prompt_path: str) -> str:
    """Load the prompt from a text file."""
    try:
        with open(prompt_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        print(f"Error reading prompt file: {e}")
        return ""


def analyze_paper(api_key: str, prompt_text: str, paper_text: str) -> PaperAnalysis:
    """Analyze a paper using OpenAI's API with structured outputs."""
    client = OpenAI(api_key=api_key)
    
    # Combine the prompt with the paper text
    full_prompt = f"{prompt_text}\n\n---PAPER CONTENT BEGINS---\n{paper_text}\n---PAPER CONTENT ENDS---"
    
    try:
        completion = client.beta.chat.completions.parse(
            model="gpt-4.1",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert research paper analyzer specializing in evaluating papers for LLM data collection projects with a focus on ethical and humanitarian principles."
                },
                {
                    "role": "user",
                    "content": full_prompt
                }
            ],
            response_format=PaperAnalysis,
        )
        
        return completion.choices[0].message.parsed
    
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        raise


def save_results(analysis: PaperAnalysis, output_path: str):
    """Save the analysis results to a JSON file."""
    try:
        with open(output_path, 'w', encoding='utf-8') as file:
            json.dump(analysis.model_dump(), file, indent=2)
        print(f"Results saved to: {output_path}")
    except Exception as e:
        print(f"Error saving results: {e}")


def main():
    # Check command line arguments
    if len(sys.argv) != 3:
        print("Usage: python analyze_paper.py <prompt_file.txt> <paper.pdf>")
        sys.exit(1)
    
    prompt_file = sys.argv[1]
    pdf_file = sys.argv[2]
    
    # Check if files exist
    if not os.path.exists(prompt_file):
        print(f"Error: Prompt file '{prompt_file}' not found.")
        sys.exit(1)
    
    if not os.path.exists(pdf_file):
        print(f"Error: PDF file '{pdf_file}' not found.")
        sys.exit(1)
    
    # Get API key from environment variable
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set.")
        sys.exit(1)
    
    # Load prompt and extract PDF text
    print("Loading prompt...")
    prompt_text = load_prompt(prompt_file)
    
    print("Extracting text from PDF...")
    paper_text = extract_text_from_pdf(pdf_file)
    
    if not paper_text:
        print("Error: Could not extract text from PDF.")
        sys.exit(1)
    
    # Analyze the paper
    print("Analyzing paper with OpenAI...")
    try:
        analysis = analyze_paper(api_key, prompt_text, paper_text)
        
        # Display results
        print("\n=== ANALYSIS RESULTS ===")
        print(f"Paper Title: {analysis.paper_title}")
        print(f"Priority Level: {analysis.priority_level.value.upper()}")
        print(f"Recommendation: {analysis.recommendation}")
        
        # Save results
        output_filename = "screened_papers/" + Path(pdf_file).stem + "_analysis.json"
        save_results(analysis, output_filename)
        
    except Exception as e:
        print(f"Analysis failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()