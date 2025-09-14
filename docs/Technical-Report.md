<a id="technical-report-top"></a>

<div align="center">
  <a href="https://github.com/fiifidawson/CHITCHAT">
    <img src="../assets/doc.png" alt="Logo" width="80" height="80">
  </a>
  <h3 align="center">Technical Report</h3>
</div>

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#project-structure">Project Structure</a>
      <ul> 
        <li><a href="#component-diagram">Component Diagriam</a></li>
        <li><a href="#architectural-description">Architectural Description</a></li>
      </ul>
    </li>
    <li>
      <a href="#methodology">Methodology</a>
      <ul>      
        <li><a href="#data-ingestion">Data Ingestion</a></li>
        <li><a href="#vector-storage-and-retrieval">Vector Storage and Retrieval</a></li>   
        <li><a href="#answer-generation">Answer Generation</a> </li>
        <li><a href="#user-interface">User Interface</a> </li>
        <li><a href="#novelty-highlights">Novelty Highlights</a> </li>         
      </ul>
    </li>
  </ol>
</details>

## Project Overview

<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

## Folder Structure

````
CHITCHAT/
    ├── analysis
    ├── bucket/
    │   ├── plots/
    │   │   ├── openai_analysis/
    │   │   │   └── plots
    │   │   └── web_scrape/
    │   │       └── plots
    │   ├── paper_analysis.py
    │   ├── web_scrape_analysis.py
    │   └── word_cloud_analysis.py      
    ├── analyze_outputs/
    │   └── screening_results
    ├── assets/
    │   └── images
    ├── data/
    │   ├── boolean.csv
    │   ├── boolean_combinations.json
    │   ├── structure.json
    │   └── test_papers.json
    ├── docs/
    │   ├── prompt/
    │   │   └── paper_screening_prompt.txt
    │   ├── Technical-Report.md
    │   └── instructions.md
    ├── output/
    │   ├── screening_results.jsonl
    │   └── unique_boolean_combinations.json
    ├── scripts/
    │   ├── screen_papers.sh
    │   └── web_scrape.sh
    ├── src/
    │   ├── api/
    │   │   ├── arxiv_paper_search.py
    │   │   └── web_scrape.py
    │   ├── boolean/
    │   │   ├── boolean_combinations.py
    │   │   ├── csv_to_json.py
    │   │   └── unique_boolean_combinations.py
    │   └── screen_papers.py
    ├── .gitignore
    ├── README.md
    ├── layout.json
    ├── playground.ipynb
    └── requirements.txt
````
<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

## Prerequisites / Setup

## Contributing

We welcome contributions!❤️ 

If you're part of the main project team, kindly reach out to **David**, **Tim**, or **Fiifi** to join the Slack channel.  

### How to Contribute
1. **Check Issues**  
   - Review the [GitHub Issues](./issues) and pick one you'd like to work on.  
   - If you encounter a new problem, [open a new issue](./issues/new) with clear details.  

2. **Get Approval**  
   - Wait for project maintainers to approve or assign the issue before starting.  

3. **Make Changes**  
   - Fork the repository.  
   - Create a new branch for your changes.  
   - Implement and test your fix or feature.  

4. **Submit a Pull Request (PR)**  
   - Open a PR describing the problem and your solution.  
   - Link the related issue in your PR description.  

### Notes  
- PRs should be small, focused, and easy to review.  
- Communication is encouraged—ask questions on Slack if you're unsure.  