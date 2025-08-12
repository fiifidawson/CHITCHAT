# CHITCHAT
ArCHitectures for  Interpretable &amp;  Transparent  Continuous  Humanitarian  Alignment  in  chatbot  Technologies

## Run as an RCP job
1. Run the `web_scrape.sh` or `screen_papers.sh` script from RCP.
2. The script to run the `web_scrape.sh` script on RCP looks like this:
```
runai submit \
  --name paper-scraping \
  --image registry.rcp.epfl.ch/multimeditron/basic:latest-arni \
  --pvc light-scratch:/mloscratch \
  --large-shm \
  -e NAS_HOME=/mloscratch/users/arni \
  -e HF_API_KEY_FILE_AT=/mloscratch/users/arni/keys/hf_key.txt \
  -e WANDB_API_KEY_FILE_AT=/mloscratch/users/arni/keys/wandb_key.txt \
  -e GITCONFIG_AT=/mloscratch/users/arni/.gitconfig \
  -e GIT_CREDENTIALS_AT=/mloscratch/users/arni/.git-credentials \
  -e VSCODE_CONFIG_AT=/mloscratch/users/arni/.vscode-server \
  --backoff-limit 0 \
  --run-as-gid 84257 \
  --gpu 0 \
  --command -- "/mloscratch/users/arni/chitchat/CHITCHAT/web_scrape.sh" \
                "/mloscratch/users/arni/chitchat/CHITCHAT/output/unique_boolean_combinations.json"
```
3. For `screen_papers.sh` you need to add a file `openai_key.txt` with an openai api key.

## Run using the command line
1. Install: `pip install openai pypdf2 pydantic`
2. Add OpenAI API key with `export OPENAI_API_KEY="your-api-key-here"`
3. Run the script with `python3 screen_papers.py path/to/paper_screening_prompt.txt path/to/papers.json`