# Setup

This guide takes you from a new computer to a first answer. Follow the section for your system: [Windows](#windows) or [macOS](#macos). Linux works like macOS.

Each step ends with a **Check**: run it before moving on, so a problem shows up where it starts.

## What you need

| | Windows | macOS |
|---|---|---|
| System | Windows 10 (22H2) or 11, 64-bit | macOS 14 (Sonoma) or later, Apple silicon (M1 or newer) |
| Memory | 16 GB recommended | 16 GB recommended |
| Free disk | about 15 GB | about 10 GB |
| Extra software | Git, uv, Docker Desktop | Git, uv (Docker is optional) |
| Account | An OpenAI API key | An OpenAI API key |

Why these:

- **uv** installs Python 3.11 and every library for you. You don't need to install Python yourself.
- **Docker Desktop** runs Milvus, the search index used by `index` and `ask`. On Windows it is required, because the file-based Milvus Lite has no Windows build. On macOS and Linux, Milvus Lite works without Docker.
- **Intel Macs are not supported**: the machine-learning library (torch) no longer ships builds for them.
- **The API key** pays for planning searches, screening papers and answering questions. A small test run costs a few cents.

First-time downloads, so you can plan for them:

| What | When | Size |
|---|---|---|
| Python libraries (`uv sync`) | Setup | a few GB, 10 to 30 minutes |
| spaCy language model | Setup | about 600 MB |
| Milvus images (Windows, Docker) | Setup | about 2 to 3 GB |
| Embedding models | First `index` | about 600 MB |
| Reranker model, if switched on | First `ask` | about 1 GB |

## Windows

Use **PowerShell** for every command (Start menu → "PowerShell"). In VS Code, use a PowerShell terminal.

### 1. Install Git

```powershell
winget install --id Git.Git -e
```

Close PowerShell and open a new one, so it finds Git.

**Check:** `git --version` prints a version.

### 2. Install uv

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Close PowerShell and open a new one.

**Check:** `uv --version` prints a version.

### 3. Get the code

```powershell
cd $HOME
git clone https://github.com/fiifidawson/CHITCHAT.git
cd CHITCHAT
```

**Check:** `dir` lists `pyproject.toml`, `configs` and `src`.

### 4. Install the libraries

```powershell
uv sync
```

This downloads Python 3.11 and every library. It takes 10 to 30 minutes.

- If it stops with "network timeout" or "RPC failed", run it again with a longer timeout: `$env:UV_HTTP_TIMEOUT = "300"; uv sync`. It continues where it stopped.

**Check:** `uv run chitchat --help` lists the commands `run`, `search`, `ask`, `status` and `report`.

### 5. Download the language model for the privacy step

```powershell
uv run python -m spacy download en_core_web_lg
```

**Check:** `uv run python -c "import spacy; spacy.load('en_core_web_lg'); print('ok')"` prints `ok`.

### 6. Add your API key

```powershell
Copy-Item .env.example .env
notepad .env
```

In Notepad, fill in the line `OPENAI_API_KEY=sk-...` with your key, save and close.

Then make sure no old key overrides it. A key set in Windows or in your terminal always wins over `.env`:

```powershell
[Environment]::GetEnvironmentVariable("OPENAI_API_KEY", "User")     # should print nothing
$env:OPENAI_API_KEY                                                  # should print nothing
```

If either prints a key, remove it:

```powershell
[Environment]::SetEnvironmentVariable("OPENAI_API_KEY", $null, "User")
Remove-Item Env:OPENAI_API_KEY
```

Then fully quit VS Code (all windows) and open it again, so new terminals don't keep the old key.

**Check:** `uv run chitchat search --mode shallow --plan-only --yes "consent in LLM training data"` shows a draft search and a "Search ready" box. This is one small LLM call. It leaves a small folder in `runs/` that you can delete. If it says `AuthenticationError`, see [Troubleshooting](#troubleshooting).

### 7. Install Docker Desktop and start Milvus

Install Docker Desktop:

```powershell
winget install -e --id Docker.DockerDesktop
```

Restart Windows if asked. Open Docker Desktop from the Start menu, accept the terms, and wait until it says "Engine running". Docker Desktop may ask you to install or update WSL 2: accept.

Then start Milvus in a folder outside the repo (Milvus keeps its data there):

```powershell
mkdir $HOME\milvus
cd $HOME\milvus
curl.exe -L https://github.com/milvus-io/milvus/releases/download/v2.6.25/milvus-standalone-docker-compose.yml -o docker-compose.yml
docker compose up -d
```

- Type `curl.exe`, not `curl`. In PowerShell, `curl` is a different command and fails with "A parameter cannot be found that matches parameter name 'L'".
- Use Milvus v2.6.24 or later. Older compose files use a MinIO image that was removed from Docker Hub ("pull access denied for minio/minio").

Make Milvus start whenever Docker Desktop starts:

```powershell
docker update --restart unless-stopped milvus-etcd milvus-minio milvus-standalone
```

**Check:** `docker compose ps` (in `$HOME\milvus`) shows `milvus-standalone`, `milvus-etcd` and `milvus-minio` as `healthy`. This can take a minute.

The configs use `index.db_uri: auto`, which means `http://127.0.0.1:19530` on Windows: the Milvus you just started. Nothing to change.

### 8. Run the checks

```powershell
cd $HOME\CHITCHAT
uv run pytest
uv run chitchat run -c configs/pipeline.smoke.yaml --stages queries
```

**Check:** the tests pass (about a minute), and the second command shows a "Boolean queries" table and a "Done" box.

You're set up. Go to [Your first run](#your-first-run).

## macOS

Use the **Terminal** app (Applications → Utilities → Terminal), or a terminal in VS Code. The commands below are for zsh, the default shell.

### 1. Install Git

```bash
xcode-select --install
```

A window asks to install the command line developer tools: click Install. If it says they are already installed, that's fine.

**Check:** `git --version` prints a version.

### 2. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Close the terminal and open a new one. (With Homebrew, `brew install uv` works too.)

**Check:** `uv --version` prints a version.

### 3. Get the code

```bash
cd ~
git clone https://github.com/fiifidawson/CHITCHAT.git
cd CHITCHAT
```

**Check:** `ls` lists `pyproject.toml`, `configs` and `src`.

### 4. Install the libraries

```bash
uv sync
```

This downloads Python 3.11 and every library. It takes 10 to 30 minutes.

- If it stops with "network timeout", run `UV_HTTP_TIMEOUT=300 uv sync`. It continues where it stopped.
- If it says there is no wheel for your platform, check that your Mac has Apple silicon and macOS 14 or later: Apple menu → About This Mac.

**Check:** `uv run chitchat --help` lists the commands `run`, `search`, `ask`, `status` and `report`.

### 5. Download the language model for the privacy step

```bash
uv run python -m spacy download en_core_web_lg
```

**Check:** `uv run python -c "import spacy; spacy.load('en_core_web_lg'); print('ok')"` prints `ok`.

### 6. Add your API key

```bash
cp .env.example .env
open -e .env
```

In TextEdit, fill in the line `OPENAI_API_KEY=sk-...` with your key, save and close.

Then make sure no old key overrides it. A key exported in your shell always wins over `.env`:

```bash
echo $OPENAI_API_KEY                         # should print an empty line
grep -n OPENAI_API_KEY ~/.zshrc ~/.zprofile  # should find nothing
```

If a key shows up, delete that `export OPENAI_API_KEY=...` line from the file, then run `unset OPENAI_API_KEY` and open a new terminal.

**Check:** `uv run chitchat search --mode shallow --plan-only --yes "consent in LLM training data"` shows a draft search and a "Search ready" box. This is one small LLM call. It leaves a small folder in `runs/` that you can delete.

### 7. Milvus: nothing to install

On macOS the configs use `index.db_uri: auto`, which means Milvus Lite: a `milvus.db` file inside each run folder. There's no server to start.

If you'd rather use a Milvus server (for example to share it between runs), install Docker Desktop for Mac, then:

```bash
mkdir -p ~/milvus && cd ~/milvus
curl -L https://github.com/milvus-io/milvus/releases/download/v2.6.25/milvus-standalone-docker-compose.yml -o docker-compose.yml
docker compose up -d
```

and set `index.db_uri: http://127.0.0.1:19530` in the configs you use.

### 8. Run the checks

```bash
cd ~/CHITCHAT
uv run pytest
uv run chitchat run -c configs/pipeline.smoke.yaml --stages queries
```

**Check:** the tests pass (about a minute), and the second command shows a "Boolean queries" table and a "Done" box.

You're set up. Go to [Your first run](#your-first-run).

## Your first run

Start with the smallest example: your documents only, no paper search. It takes about 3 minutes and costs under a cent.

Windows (PowerShell) and macOS (Terminal) use the same commands here:

```bash
uv run chitchat run -c examples/own-documents/pipeline.yaml --stages ingest,sanitize,export,index
uv run chitchat ask -c examples/own-documents/pipeline.yaml "What consent approach was agreed with the community in Kakuma?"
```

You should see 7 documents read, about 80 items masked, and an answer citing `[D0004]`. Then try a real search:

```bash
uv run chitchat search --mode shallow "Which methods reduce bias when collecting training data for language models in low-resource languages?"
```

[examples/README.md](../examples/README.md) walks through this and a thorough example step by step.

## Updating

```bash
git pull
uv sync
```

Your runs in `runs/` and your documents in `my_docs/` are not touched.

## Troubleshooting

| What you see | What it means | What to do |
|---|---|---|
| `AuthenticationError` … "Check the API key" | OpenAI rejected the key | If the message says the key is set in your environment, remove it (step 6). Otherwise check the key in `.env`, or create a new one |
| `RateLimitError` / `insufficient_quota` | The key works but the account has no credit | Add credit in your OpenAI account |
| "milvus-lite is required" or "Milvus Lite doesn't run on Windows" | A config points at a `milvus.db` file on Windows | Set `index.db_uri: auto` (or `http://127.0.0.1:19530`) and start Milvus in Docker |
| "Fail connecting to server on 127.0.0.1:19530" | Milvus isn't running | Start Docker Desktop, then `docker start milvus-etcd milvus-minio milvus-standalone` |
| `docker: command not found` / "cannot connect to the Docker daemon" | Docker Desktop isn't running | Open Docker Desktop and wait for "Engine running" |
| "pull access denied for minio/minio" | An old Milvus compose file | Download the v2.6.25 compose file (step 7) |
| "A parameter cannot be found that matches parameter name 'L'" | PowerShell's `curl` | Type `curl.exe` |
| `uv sync`: "network timeout" or "RPC failed" | Slow or unstable network | Run again with `UV_HTTP_TIMEOUT=300` set |
| "OpenAlex will return nothing for N categories" | Those queries are over OpenAlex's 1,500-character limit | Searches from `chitchat search` are fitted automatically. For the predefined search, shorten the synonyms |
| "Privacy mode sent your question as … [PERSON_1]" | A word in your question was taken for a name | Rephrase ("the MoodSmith system"), or use `--no-privacy` |
| Nothing happens for minutes during `ingest` | mmore is starting its document readers | Normal on the first run: wait 2 to 3 minutes |
| No wheel for torch on a Mac | An Intel Mac, or macOS before 14 | Use an Apple silicon Mac with macOS 14+, or Windows |

Still stuck? `uv run chitchat status -c <config>` shows what each stage produced, and every run's full output is saved in `runs/<run>/logs/`.
