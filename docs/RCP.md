# Running on EPFL RCP (one H100)

This guide runs a full CHITCHAT review on EPFL's RCP cluster with one H100 80 GB GPU. The model is Qwen3.6 27B, served by vLLM with its full 262k-token context. Everything runs on the cluster, so it uses none of your laptop's internet data.

It follows the LiGHT guide for connecting to RCP: https://lighters-playground.github.io/LiGHT-doc/clusters/rcp/rcp/

Problems seen while setting this up are marked ⚠ next to the step where they happen. The table at the end lists them by error message.

## Paths

Your scratch folder is the same disk under two names:

| Where you are | Path |
|---|---|
| The jumphost (after `ssh`) | `/mnt/light/scratch/users/$USER` |
| Inside a job (after `runai bash`) | `/lightscratch/users/$USER` |

Below, `$S` means that folder. Keep everything on it: the folder you land in inside a job (`/workspace`) and your home folder are wiped when the job stops.

## A. Get into a GPU job

1. SSH to the jumphost.
   - ⚠ Don't install or run anything there. It has no GPU, so vLLM fails with "Failed to infer device type".
2. Optional: start tmux on the jumphost (`tmux new -s chitchat`). It keeps your `runai bash` connection open if your laptop disconnects.
3. Submit a GPU job as the LiGHT guide shows, with `--node-pool h100 --gpu 1 --pvc light-scratch:/lightscratch`. Then run `runai bash <job-name>`.
   - ⚠ GPU jobs stop after 2 hours without GPU use. Start the run soon after the model server is up.
4. Check that you are in the job: `nvidia-smi -L` lists the H100, and `ls /lightscratch` works.

## B. One-time setup (inside the job)

5. Write the settings file. It is one command: paste it all at once.

   ```bash
   cat > /lightscratch/users/$USER/rcp-env.sh <<'EOF'
   export USER=${USER:-$(whoami)}           # runai bash leaves USER empty
   # The same scratch is /lightscratch inside a job and /mnt/light/scratch on the jumphost.
   if [ -d /lightscratch/users/$USER ]; then export S=/lightscratch/users/$USER; else export S=/mnt/light/scratch/users/$USER; fi
   export PATH=$S/bin:$PATH
   export HF_HOME=$S/hf
   export UV_CACHE_DIR=$S/.cache/uv
   export PIP_CACHE_DIR=$S/.cache/pip
   export UV_PYTHON_INSTALL_DIR=$S/.uv-python
   export XDG_CACHE_HOME=$S/.cache
   export SETUPTOOLS_USE_DISTUTILS=local    # the image sets stdlib; Python 3.12 has none
   export VLLM_USE_FLASHINFER_SAMPLER=0     # the image's nvcc can't compile FlashInfer's sampler
   EOF
   source /lightscratch/users/$USER/rcp-env.sh
   ```

   - ⚠ If a pasted line starts with `[200~`, your terminal garbled the paste. Paste one line at a time.
6. Install uv on scratch, so it survives the job:

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=$S/bin UV_NO_MODIFY_PATH=1 sh
   uv --version
   ```

7. Make the vLLM environment. Do this inside the job: an environment only works at the path it was made on.

   ```bash
   cd $S
   uv venv --python 3.12 $S/vllm-env && source $S/vllm-env/bin/activate
   uv pip install vllm --torch-backend=auto
   python -c "import torch; print(torch.version.cuda, torch.cuda.is_available())"   # a CUDA version and True
   vllm download-kernels          # prebuilt FlashInfer kernels; if this errors, carry on
   ```

   - ⚠ Without `--torch-backend=auto`, uv can pick a PyTorch build that doesn't match the GPU.
   - ⚠ Don't check the install with `import vllm._C`: that module doesn't exist in vLLM 0.34, even when all is well.
8. Set up CHITCHAT. Use a new terminal, or run `deactivate` first.

   ```bash
   source /lightscratch/users/$USER/rcp-env.sh
   unset LD_LIBRARY_PATH          # in the CHITCHAT terminal only
   cd $S/chitchat                 # your clone of this repo
   uv sync
   uv run python -c "import torch; print(torch.__version__)"   # 2.x.x+cpu
   ```

   - ⚠ `torch._C has no attribute TensorBase` means `LD_LIBRARY_PATH` is still set. The image's value loads the image's own PyTorch. Reinstalling doesn't help; unsetting it does. Don't unset it where vLLM runs.
   - ⚠ `VIRTUAL_ENV ... does not match the project environment` means the vLLM environment is still active. Run `deactivate`. It is harmless, but the two should stay apart.
   - CHITCHAT's PyTorch is the CPU build on purpose. It only computes embeddings in the index stage, and leaves the GPU to vLLM.
## C. Each time: start the model server

9. Start vLLM in the background, then watch its log:

    ```bash
    source /lightscratch/users/$USER/rcp-env.sh && source $S/vllm-env/bin/activate
    cd $S
    nohup vllm serve Qwen/Qwen3.6-27B-FP8 --max-model-len 262144 --reasoning-parser qwen3 --max-num-seqs 64 --default-chat-template-kwargs '{"enable_thinking": false}' > $S/vllm.log 2>&1 &
    tail -f $S/vllm.log
    ```

    The first start downloads about 30 GB into `$S/hf`. Later starts reuse it.

10. Wait for `Application startup complete`, then press `Ctrl+c`. That stops the log, not the server. Check it: `curl -s localhost:8000/v1/models` lists `Qwen/Qwen3.6-27B-FP8`.

## D. Each time: plan and run

11. Get the CHITCHAT terminal ready:

    ```bash
    deactivate 2>/dev/null
    source /lightscratch/users/$USER/rcp-env.sh
    unset LD_LIBRARY_PATH
    cd $S/chitchat
    ```

12. Plan the search. It asks clarifying questions, then shows a draft of the search, then a draft of the screening criteria for your question. For each: `a` accepts, `c` asks for changes, `q` quits. Stay with it: it takes a few minutes, and a dropped connection ends it.

    ```bash
    uv run chitchat search -c configs/pipeline.rcp.yaml --plan-only "your question"
    ```

    It ends with `Run it, or carry on after a stop: chitchat run -c runs/<folder>/pipeline.yaml`.

    [configs/pipeline.rcp.yaml](../configs/pipeline.rcp.yaml) runs the full deep search (3 to 6 categories, 25 results per source, 2 pages). Masking is off (`privacy.mask: false`), and the command says so before anything is sent.

13. Start the run in the background, with that path:

    ```bash
    nohup uv run chitchat run -c runs/<folder>/pipeline.yaml > $S/run.log 2>&1 &
    tail -f $S/run.log
    ```

    Once the log moves, press `Ctrl+c` and disconnect. The run carries on.

    - ⚠ Keep `uv run` in front of `chitchat`.
    - ⚠ If the shell prints `[2]` or higher, another background job exists. `ps aux | grep -E "[v]llm serve|[c]hitchat run"` should show one of each. Stop a second `chitchat run` with `kill <PID>`.
    - A Google Scholar warning is expected: Scholar blocks scripts. The other sources carry on.
    - If the run stops for any reason (an error, a killed process, a stopped job), run the same `nohup uv run chitchat run -c runs/<folder>/pipeline.yaml ...` line again. Stages already done are skipped, and screening carries on with the papers not screened yet.

## E. Coming back

14. Reconnect: `tmux attach -t chitchat` on the jumphost, or `runai bash <job-name>`. Check the job is alive with `runai list jobs` (`runai login` if it says unauthorized).
    - ⚠ In a new `runai bash` shell, `$USER` can be empty. Run `export USER=$(whoami)` before `source /lightscratch/users/$USER/rcp-env.sh`.
15. Follow the run: `tail -f /lightscratch/users/$USER/run.log`. Check it is still going: `ps aux | grep "[c]hitchat run"`.
    - ⚠ Avoid tmux inside the job. A session there once disappeared and stopped vLLM with it. `nohup` doesn't depend on any terminal. With tmux on the jumphost and inside the job, `Ctrl+b` reaches the outer one; press `Ctrl+b` twice for the inner one.

## F. The results

Everything is in the run folder, `$S/chitchat/runs/<folder>/`:

| File | What it is |
|---|---|
| `answer/brief.md` | The decision brief: the answer to your question |
| `answer/brief.json` | The same brief as data |
| `answer/trace.jsonl` | How the brief was written, step by step |
| `prisma.md` | The PRISMA counts: found, removed, screened, included |
| `dataset.csv` | One row per paper, with its screening label and the extracted answers |
| `screening.jsonl` | Every screening decision, with the quotes behind it |
| `sources.json` | The `P0001`, `D0001` tags cited in the brief, with titles and DOIs |
| `search/` | The search plan and the screening criteria (`criteria.yaml`) you accepted |
| `privacy_report.json` | What was masked before the model saw it, or `"masking": "off"` |
| `raw/pdfs/`, `milvus.db` | Downloaded PDFs and the search index: large, rarely needed on your laptop |

The run is finished when `ls answer/brief.md` finds the file and `run.log` ends with the answer stage.

To copy the results to your laptop, go through the jumphost path. In PowerShell:

```powershell
scp -r "<you>@<jumphost>:/mnt/light/scratch/users/<you>/chitchat/runs/<folder>/{answer,search,prisma.md,dataset.csv,screening.jsonl,sources.json,privacy_report.json}" .\rcp-results\
```

This leaves out `raw/` and `milvus.db`.

## G. Clean up

16. Stop the server in the job: `pkill -f "vllm serve"`.
17. End the job on the jumphost: `runai delete job <job-name>`. A job with a GPU holds that GPU until you do.

## Errors and fixes

| Error | Cause | Fix |
|---|---|---|
| `/lightscratch/users//rcp-env.sh: No such file` | `$USER` is empty in the `runai bash` shell | `export USER=$(whoami)`, then `source` again |
| `uv: command not found` | uv isn't in the image | Step 6, then `source rcp-env.sh` |
| `Failed to infer device type` | You are on the jumphost, which has no GPU | Run it inside a job (step 3) |
| `No module named 'vllm._C'` | Not an error in vLLM 0.34 | Check with the PyTorch line in step 7 instead |
| `No module named 'distutils'` | The image sets `SETUPTOOLS_USE_DISTUTILS=stdlib` | `source rcp-env.sh` (sets it to `local`) |
| `nvcc fatal: Unknown option '--compress-mode=size'` | FlashInfer compiles with the image's older CUDA compiler | `source rcp-env.sh` (`VLLM_USE_FLASHINFER_SAMPLER=0`), and `vllm download-kernels` |
| `max_num_seqs (1024) exceeds available Mamba cache blocks` | vLLM's default number of parallel requests doesn't fit next to the full context | Add `--max-num-seqs 64` (CHITCHAT sends at most 8) |
| Out of GPU memory when vLLM starts | The context is too large | `--max-model-len 131072`. Don't go lower: the model card says thinking suffers |
| `torch._C has no attribute TensorBase` | The image's `LD_LIBRARY_PATH` loads its own PyTorch | `unset LD_LIBRARY_PATH` in the CHITCHAT terminal |
| `VIRTUAL_ENV ... does not match` | The vLLM environment is active | `deactivate` |
| `tmux attach` says `no sessions` | The tmux session in the job is gone | Use `nohup` (steps 9 and 13); check vLLM with `curl` |
| `^B` printed on screen | You are not inside tmux | Start or attach tmux first, or use `nohup` |
| `The model's replies were cut off ... 3 times` (the run stops) | Qwen's thinking runs on until the reply is cut off | Start vLLM with thinking off (the `--default-chat-template-kwargs` part of step 9), or raise `llm.max_new_tokens` in the run's `pipeline.yaml`. Then run the same `chitchat run -c runs/<folder>/pipeline.yaml` again: papers already screened are kept |
| `Nothing to index: no papers labelled HIGH, MEDIUM, LOW` | Every paper was excluded. `chitchat search` drafts criteria for your question; this happened when the fixed `criteria.example.yaml` (about LLM data) screened another topic, or with a `must` question that is too narrow | Edit the `decision` rules in `runs/<folder>/search/criteria.yaml`, run `chitchat run -c runs/<folder>/pipeline.yaml --redecide` (no LLM calls), then the same command without `--redecide` |
| `The model ran out of room` | The model's context is too small | Check `--max-model-len` in the `vllm serve` line |
