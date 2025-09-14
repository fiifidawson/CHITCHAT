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

---

# Project Overview

---

<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

# Folder Structure

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

---

# Prerequisites / Setup
## Virtual Environment Setup
### Linux/Unix Systems
1. **Prerequisites**
    Update your system and install Python 3.10 with venv support:
    ```bash
    sudo apt update
    sudo apt install python3.10 python3.10-venv
    ```

2. **Create Virtual Environment**
    ```bash
    python3.10 -m venv .venv
    ```

3. **Activate Virtual Environment**
    ```bash
    source .venv/bin/activate
    ```
4. **Install Dependencies**
    ```bash
    pip install -r requirements.txt 
    ```

5. **Deactivate Virtual Environment**
    ```bash
    deactivate
    ```
<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

### Windows Systems

1. **Create Virtual Environment**
    ```cmd
    python -m venv .venv
    ```

2. **Activate Virtual Environment**
    ```cmd
    .venv\Scripts\activate
    ```
3. **Install Dependencies**
    ```cmd
    pip install -r requirements.txt 
    ```

4. **Deactivate Virtual Environment**
    ```cmd
    deactivate
    ```
<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

---

## Running Locally

---

## Running on RCP
### Setting up RCP
Before setting up the RCP, contact the project lead to be added to the RCP(Research Computing Platform).
[Click here to learn about setting up RCP](https://github.com/MichelDucartier/rcp-docker-images/blob/master/LIGHT_README.md)

### Run as an RCP job
1. Run the `web_scrape.sh` or `screen_papers.sh` script from RCP.
2. The script to run the `web_scrape.sh` script on RCP looks like this (change USER):
```
runai submit \
  --name paper-scraping \
  --image registry.rcp.epfl.ch/multimeditron/basic:latest-USER \
  --pvc light-scratch:/mloscratch \ # <- CAN ALSO BE LIGHTSCRATCH
  --large-shm \
  -e NAS_HOME=/mloscratch/users/USER \
  -e HF_API_KEY_FILE_AT=/mloscratch/users/USER/keys/hf_key.txt \
  -e WANDB_API_KEY_FILE_AT=/mloscratch/users/USER/keys/wandb_key.txt \
  -e GITCONFIG_AT=/mloscratch/users/USER/.gitconfig \
  -e GIT_CREDENTIALS_AT=/mloscratch/users/USER/.git-credentials \
  -e VSCODE_CONFIG_AT=/mloscratch/users/USER/.vscode-server \
  --backoff-limit 0 \
  --run-as-gid 84257 \
  --gpu 0 \
  --command -- "/mloscratch/users/USER/CHITCHAT/web_scrape.sh" \
                "/mloscratch/users/USER/CHITCHAT/output/unique_boolean_combinations.json"
```
3. For `screen_papers.sh` you need to add a file `openai_key.txt` with an openai api key.

<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

---

# Contributing

We welcome contributions!❤️ 

If you're part of the main project team, kindly reach out to **David**, **Tim**, or **Fiifi** to join the Slack channel.  

## How to Contribute
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

## Notes  
- PRs should be small, focused, and easy to review.  
- Communication is encouraged—ask questions on Slack if you're unsure.  
<p align="right">[<a href="#technical-report-top">back to top</a>]</p>