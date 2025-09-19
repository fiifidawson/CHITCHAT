import argparse
import os

import pandas as pd
import json

import outlines
import openai
from tqdm import tqdm

from extraction_format import ExtractedTradeOffs

def extract_high_impact_paper(classification_path, paper_data_path):
    classification = []
    with open(classification_path, 'r', encoding='utf-8') as file:
        for line in file:
            try:
                classification.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"Error parsing line: {line}")
    classification_df = pd.DataFrame(classification)

    with open(paper_data_path, 'r') as f:
        data_df = pd.DataFrame(json.load(f))

    high_prio_df = classification_df.loc[classification_df['final_priority'] == 'HIGH PRIORITY']
    high_prio_df = data_df.join(high_prio_df.set_index('title'), on='title', how='inner')

    # remove duplicates, using url as unique identifier
    high_prio_df = high_prio_df.drop_duplicates(subset=['url'])

    return high_prio_df




def extract_tradeoffs(api_key, classification_path, paper_data_path, output_path, prompt_text_path):
    high_prio_paper = extract_high_impact_paper(classification_path, paper_data_path)

    # Create the client
    client = openai.OpenAI(
        api_key=api_key)

    # Create the model
    model = outlines.from_openai(
        client,
        "gpt-5-mini-2025-08-07"
    )

    with open(prompt_text_path) as f:
        extraction_prompt = f.read()

    paper_prompt = lambda title, abstract, extracted_text: \
        f"\n INPUT: \n Paper Title: {title}, Paper Abstract: {abstract}, Paper Text: {extracted_text}"

    print('extract ethical trade offs')
    for index, row in tqdm(high_prio_paper.iterrows()):
        prompt = extraction_prompt + paper_prompt(row.title, row.abstract, row.extracted_text)
        result = model(prompt, ExtractedTradeOffs)
        tradeoff_list = ExtractedTradeOffs.model_validate_json(result).tradeoffs
        res_df = pd.DataFrame([rec.model_dump() for rec in tradeoff_list])
        cols = list(res_df.columns)
        res_df['paper_id'] = index
        res_df['title'] = row.title
        res_df['authors'] = row.authors
        res_df['year'] = row.year
        res_df['url'] = row.url
        res_df = res_df[['paper_id', 'title', 'authors', 'year', 'url'] + cols]

        header = not os.path.exists(output_path)
        res_df.to_csv(output_path, mode='a', header=header, index=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--api-key",
        type=str,
        required=True,
        help="OpenAI API key"
    )
    parser.add_argument(
        "--classification_path",
        type=str,
        default="classification_data.jsonl",
        help="Path to the paper classification data"
    )

    parser.add_argument(
        "--paper_data_path",
        type=str,
        default="obtained_lit.json",
        help="Path to crawled paper data"
    )

    parser.add_argument(
        "--prompt_text_path",
        type=str,
        default="structured_extraction_prompt.txt",
        help="Path to the prompt file."
    )
    parser.add_argument(
        "--output-path",
        type=str,
        default="processed_results.csv",
        help="Path for the output CSV file."
    )

    args = parser.parse_args()

    extract_tradeoffs(args.api_key, args.classification_path, args.paper_data_path, args.output_path, args.prompt_text_path)
