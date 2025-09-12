# CHITCHAT
ArCHitectures for  Interpretable &amp;  Transparent  Continuous  Humanitarian  Alignment  in  chatbot  Technologies

<div align="center">
    <img src="assets/logo.png" alt=" Logo" width="750" height="90">
    <br>
    <a href="https://github.com/fiifidawson/CHITCHAT/tree/main/docs"><strong>Explore the docs »</strong></a>
</div>

## Setting up RCP
Before setting up the RCP, contact the project lead to be added to the RCP(Research Computing Platform).
[Click here to learn about setting up RCP](https://github.com/MichelDucartier/rcp-docker-images/blob/master/LIGHT_README.md)

## Run as an RCP job
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

<p align="right">[<a href="#readme-top">back to top</a>]</p>

## Run using the command line
1. Install: `pip install openai pypdf2 pydantic`
2. Add OpenAI API key with `export OPENAI_API_KEY="your-api-key-here"`
3. Run the script with `python3 screen_papers.py path/to/paper_screening_prompt.txt path/to/papers.json`

<p align="right">[<a href="#readme-top">back to top</a>]</p>