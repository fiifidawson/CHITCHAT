import os
import sys
import json
import time
import base64
from pathlib import Path
from typing import List, Optional, Literal, Dict
from enum import Enum
from datetime import datetime
from urllib.parse import urlparse

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


def load_prompt(prompt_path: str) -> str:
    """Load the prompt from a text file."""
    try:
        with open(prompt_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        print(f"Error reading prompt file: {e}")
        return ""


def analyze_paper_from_url(api_key: str, prompt_text: str, pdf_url: str) -> PaperAnalysis:
    """Analyze a paper using OpenAI's API with direct PDF URL input."""
    client = OpenAI(api_key=api_key)
    
    try:
        # Using the new responses API with direct PDF file input
        response = client.responses.create(
            model="gpt-4.1",
            input=[
                {
                    "role": "system",
                    "content": "You are an expert research paper analyzer specializing in evaluating papers for LLM data collection projects with a focus on ethical and humanitarian principles."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_file",
                            "file_url": pdf_url
                        },
                        {
                            "type": "input_text",
                            "text": prompt_text
                        }
                    ]
                }
            ],
            # Parse the response as structured output
            text={
                "format": PaperAnalysis
            }
        )
        
        # Extract the parsed response
        return response.output_parsed
    
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        raise


def analyze_paper_from_file(api_key: str, prompt_text: str, pdf_path: str) -> PaperAnalysis:
    """Analyze a paper from a local file using base64 encoding."""
    client = OpenAI(api_key=api_key)
    
    try:
        # Read and encode the PDF file
        with open(pdf_path, 'rb') as f:
            pdf_data = f.read()
        
        base64_string = base64.b64encode(pdf_data).decode('utf-8')
        filename = Path(pdf_path).name
        
        # Using the new responses API with base64-encoded PDF
        response = client.responses.create(
            model="gpt-4.1",
            input=[
                {
                    "role": "system",
                    "content": "You are an expert research paper analyzer specializing in evaluating papers for LLM data collection projects with a focus on ethical and humanitarian principles."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_file",
                            "filename": filename,
                            "file_data": f"data:application/pdf;base64,{base64_string}"
                        },
                        {
                            "type": "input_text",
                            "text": prompt_text
                        }
                    ]
                }
            ],
            # Parse the response as structured output
            text={
                "format": PaperAnalysis
            }
        )
        
        # Extract the parsed response
        return response.output_parsed
    
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        raise


def save_results(analysis: PaperAnalysis, output_path: str, source: str):
    """Save the analysis results to a JSON file."""
    try:
        # Add source information to the analysis
        analysis_dict = analysis.model_dump()
        analysis_dict['source'] = source
        analysis_dict['analysis_timestamp'] = datetime.now().isoformat()
        
        with open(output_path, 'w', encoding='utf-8') as file:
            json.dump(analysis_dict, file, indent=2)
        return True
    except Exception as e:
        print(f"Error saving results: {e}")
        return False


def get_arxiv_pdf_url(arxiv_id: str) -> str:
    """Convert arXiv ID to PDF URL."""
    arxiv_id = arxiv_id.replace('arxiv:', '').replace('arXiv:', '')
    if '/' in arxiv_id:  # Old format
        return f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    else:  # New format
        return f"https://arxiv.org/pdf/{arxiv_id}.pdf"


def process_input_file(input_file: str) -> List[Dict[str, str]]:
    """Process a file containing paper paths or URLs."""
    papers = []
    
    with open(input_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):  # Skip empty lines and comments
                continue
                
            if line.startswith('http://') or line.startswith('https://'):
                papers.append({'type': 'url', 'source': line})
            elif 'arxiv' in line.lower():
                pdf_url = get_arxiv_pdf_url(line)
                papers.append({'type': 'url', 'source': pdf_url})
            elif line.endswith('.pdf'):
                papers.append({'type': 'file', 'source': line})
            else:
                print(f"  WARNING: Skipping unrecognized input: {line}")
    
    return papers


def create_summary_report(results: List[Dict], output_path: str):
    """Create a summary report of all analyzed papers."""
    summary = {
        'total_papers': len(results),
        'analysis_date': datetime.now().isoformat(),
        'priority_breakdown': {
            'high': 0,
            'medium': 0,
            'low': 0,
            'exclude': 0
        },
        'papers_by_priority': {
            'high': [],
            'medium': [],
            'low': [],
            'exclude': []
        }
    }
    
    for result in results:
        priority = result['priority_level']
        summary['priority_breakdown'][priority] += 1
        summary['papers_by_priority'][priority].append({
            'source': result['source'],
            'title': result['paper_title'],
            'recommendation': result['recommendation']
        })
    
    with open(output_path, 'w', encoding='utf-8') as file:
        json.dump(summary, file, indent=2)
    
    return summary


def process_batch_from_file(input_file: str, prompt_file: str, output_folder: str):
    """Process all papers listed in an input file."""
    # Create output folder
    Path(output_folder).mkdir(parents=True, exist_ok=True)
    
    # Get API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set.")
        sys.exit(1)
    
    # Load prompt
    print("Loading prompt...")
    prompt_text = load_prompt(prompt_file)
    if not prompt_text:
        print("Error: Could not load prompt.")
        sys.exit(1)
    
    # Process input file
    papers = process_input_file(input_file)
    print(f"Found {len(papers)} papers to process")
    
    results = []
    failed_papers = []
    
    for i, paper_info in enumerate(papers, 1):
        print(f"\n[{i}/{len(papers)}] Processing: {paper_info['source']}")
        
        try:
            # Analyze based on type
            if paper_info['type'] == 'url':
                print("  Analyzing PDF from URL...")
                analysis = analyze_paper_from_url(api_key, prompt_text, paper_info['source'])
            else:
                print("  Analyzing local PDF file...")
                analysis = analyze_paper_from_file(api_key, prompt_text, paper_info['source'])
            
            # Generate output filename
            if paper_info['type'] == 'url':
                parsed_url = urlparse(paper_info['source'])
                if 'arxiv' in parsed_url.netloc:
                    filename = parsed_url.path.split('/')[-1].replace('.pdf', '')
                else:
                    filename = parsed_url.path.split('/')[-1].replace('.pdf', '') or 'paper'
            else:
                filename = Path(paper_info['source']).stem
            
            # Save result
            output_path = Path(output_folder) / f"{filename}_analysis.json"
            if save_results(analysis, str(output_path), paper_info['source']):
                print(f"  ✓ Analysis saved: {output_path.name}")
                print(f"  Priority: {analysis.priority_level.value.upper()}")
                
                analysis_dict = analysis.model_dump()
                analysis_dict['source'] = paper_info['source']
                results.append(analysis_dict)
            
            # Rate limiting
            if i < len(papers):
                time.sleep(1)
                
        except Exception as e:
            print(f"  ERROR: Failed to process paper: {e}")
            failed_papers.append(paper_info['source'])
    
    # Create summary
    print("\n" + "="*50)
    print("Creating summary report...")
    summary_path = Path(output_folder) / "summary_report.json"
    summary = create_summary_report(results, str(summary_path))
    
    print(f"\nAnalysis Complete!")
    print(f"Total papers processed: {len(results)}/{len(papers)}")
    print(f"Failed papers: {len(failed_papers)}")
    if failed_papers:
        print("Failed papers:")
        for f in failed_papers:
            print(f"  - {f}")
    
    print(f"\nPriority Breakdown:")
    for priority, count in summary['priority_breakdown'].items():
        print(f"  {priority.upper()}: {count} papers")
    
    print(f"\nResults saved to: {output_folder}/")


def main():
    print("\nPaper Analysis Tool - Direct PDF Support")
    print("Supports: PDF URLs, arXiv IDs, and local PDF files\n")
    
    if len(sys.argv) < 3:
        print("Usage:")
        print("  Single URL:    python analyze_paper.py <prompt_file.txt> <pdf_url>")
        print("  Single file:   python analyze_paper.py <prompt_file.txt> <paper.pdf>")
        print("  Batch:         python analyze_paper.py batch <prompt_file.txt> <input_file.txt> [output_folder]")
        print("\nFor batch mode, create a text file with one entry per line:")
        print("  - Direct PDF URLs: https://arxiv.org/pdf/2301.12345.pdf")
        print("  - arXiv IDs: 2301.12345 or arXiv:2301.12345")
        print("  - Local files: /path/to/paper.pdf")
        sys.exit(1)
    
    if sys.argv[1] == "batch":
        # Batch mode
        if len(sys.argv) < 4:
            print("Usage: python analyze_paper.py batch <prompt_file.txt> <input_file.txt> [output_folder]")
            sys.exit(1)
        
        prompt_file = sys.argv[2]
        input_file = sys.argv[3]
        output_folder = sys.argv[4] if len(sys.argv) > 4 else "screened_papers"
        
        if not os.path.exists(prompt_file):
            print(f"Error: Prompt file '{prompt_file}' not found.")
            sys.exit(1)
        
        if not os.path.exists(input_file):
            print(f"Error: Input file '{input_file}' not found.")
            sys.exit(1)
        
        process_batch_from_file(input_file, prompt_file, output_folder)
        
    else:
        # Single paper mode
        prompt_file = sys.argv[1]
        source = sys.argv[2]
        
        if not os.path.exists(prompt_file):
            print(f"Error: Prompt file '{prompt_file}' not found.")
            sys.exit(1)
        
        # Get API key
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("Error: OPENAI_API_KEY environment variable not set.")
            sys.exit(1)
        
        # Load prompt
        print("Loading prompt...")
        prompt_text = load_prompt(prompt_file)
        
        # Determine if it's a URL or file
        if source.startswith('http://') or source.startswith('https://'):
            is_url = True
        elif 'arxiv' in source.lower() and not source.endswith('.pdf'):
            source = get_arxiv_pdf_url(source)
            is_url = True
        else:
            is_url = False
            if not os.path.exists(source):
                print(f"Error: PDF file '{source}' not found.")
                sys.exit(1)
        
        print(f"Processing: {source}")
        
        try:
            if is_url:
                print("Analyzing PDF from URL...")
                analysis = analyze_paper_from_url(api_key, prompt_text, source)
            else:
                print("Analyzing local PDF file...")
                analysis = analyze_paper_from_file(api_key, prompt_text, source)
            
            print("\n=== ANALYSIS RESULTS ===")
            print(f"Paper Title: {analysis.paper_title}")
            print(f"Priority Level: {analysis.priority_level.value.upper()}")
            print(f"Recommendation: {analysis.recommendation}")
            
            # Save results
            output_folder = "screened_papers"
            Path(output_folder).mkdir(parents=True, exist_ok=True)
            
            if is_url:
                parsed_url = urlparse(source)
                if 'arxiv' in parsed_url.netloc:
                    filename = parsed_url.path.split('/')[-1].replace('.pdf', '')
                else:
                    filename = 'analyzed_paper'
            else:
                filename = Path(source).stem
            
            output_path = Path(output_folder) / f"{filename}_analysis.json"
            save_results(analysis, str(output_path), source)
            
        except Exception as e:
            print(f"Analysis failed: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()