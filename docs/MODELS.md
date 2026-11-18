# Models

CHITCHAT uses open-weight models by default, served on your own computer or on a server you control. The aim is a fair comparison with existing systems, with data that stays where you put it.

## The short version

- **Default:** `qwen3.5:9b` on [Ollama](https://ollama.com), on your computer. Free, Apache 2.0, about 7 GB. Nothing leaves the machine.
- **One setting for every step.** The top-level `llm:` block in your config is used for search planning, screening, the answer agents, `ask` and the evaluation judge. A section can override it (for example `evaluate.judge_llm`).
- **To change model**, copy a block from [configs/models/](../configs/models/) into the `llm:` section of your config.

```yaml
llm:
  llm_name: qwen3.5:9b
  base_url: http://localhost:11434/v1   # Ollama
  temperature: 0
```

Before any LLM stage, CHITCHAT checks that the model server answers and that the model is there. If not, it stops with a plain message, such as "Is Ollama running?" or "Run: ollama pull qwen3.5:9b".

## Which model

All of these are open-weight models with permissive licences.

| Model | Ollama tag | Licence | Download | Runs well on | Notes |
|---|---|---|---|---|---|
| Qwen3.5 9B | `qwen3.5:9b` | Apache 2.0 | about 7 GB | Apple silicon with 16 GB, or an NVIDIA GPU with 8 GB+ | The default. Good at structured output |
| Qwen3.5 4B | `qwen3.5:4b` | Apache 2.0 | about 4 GB | Laptops with 8 GB, or CPU only | Faster, a little weaker |
| gpt-oss 20B | `gpt-oss:20b` | Apache 2.0 | about 14 GB | 16 GB+ of GPU or unified memory | Strong reasoning, slower |
| Gemma 4 12B | `gemma4:12b` | see Google's model page | about 8 GB | Apple silicon, NVIDIA GPU | Check the licence on Google's model page before use |
| Qwen3.5 27B | `Qwen/Qwen3.5-27B` on vLLM | Apache 2.0 | about 55 GB | One GPU server (48 to 80 GB) | For the best local quality |
| gpt-oss 120B | `openai/gpt-oss-120b` on vLLM | Apache 2.0 | about 65 GB | One 80 GB GPU | Strongest open option here |

How to choose:

- **Start with the default.** Move up only if the briefs or the screening look weak.
- **Use the same model for every system you compare**, and record it: every output (screening records, `brief.json`, `summary.md`) names the model.
- **The evaluation judge** is better from another model family than the one that wrote the answers. It limits self-preference. Set `evaluate.judge_llm`.

## How fast it is

Speed depends on your hardware, not on CHITCHAT.

| Hardware | What to expect with `qwen3.5:9b` |
|---|---|
| Apple silicon (M1 or newer), 16 GB | Comfortable: seconds to a minute per call |
| NVIDIA GPU, 8 GB+ | Fast |
| CPU only (no GPU) | Slow: several minutes per call. A full answer loop can take an hour. Use `qwen3.5:4b`, a GPU server, or a hosted provider |

Structured output (JSON that must match a schema) is slower than plain text on a CPU. `ollama ps` shows whether the model runs on `GPU` or `CPU`.

## Context length

Ollama's default context window is small (4,096 tokens). Longer prompts are cut without warning, so raise it to 16,384 once:

- Windows: `setx OLLAMA_CONTEXT_LENGTH 16384`, then quit Ollama from the system tray and open it again.
- macOS: `launchctl setenv OLLAMA_CONTEXT_LENGTH 16384`, then quit Ollama from the menu bar and open it again.
- Or in the Ollama app: Settings → Context length.

`ollama ps` shows the context in use. The shipped configs set `screening.max_chars: 24000` so each paper fits in 16k tokens. With a larger context (vLLM with `--max-model-len 32768`), you can raise it to 60000.

## Ways to serve a model

| Option | Where it runs | Data | Cost | Use it for |
|---|---|---|---|---|
| **Ollama** (default) | Your computer: Windows, macOS, Linux | Stays on the machine | Free | Everyday use and small runs |
| **vLLM** | A Linux server with an NVIDIA GPU (on Windows, WSL2) | Stays on your server | Your hardware | Large runs, bigger models, a shared team server |
| **Hosted open models** | A provider's servers | Leaves your network | Pay per token, often free tiers | When you have no GPU. Only with the rules below |

vLLM, in short:

```bash
pip install vllm
vllm serve Qwen/Qwen3.5-27B --max-model-len 32768
```

Then use [configs/models/vllm.yaml](../configs/models/vllm.yaml) with your server's address. Keep the server on a private network: it has no login by default.

## Hosted providers: the rules

Masked text only reaches a provider. Still, a hosted provider sees every prompt. Use one only if all of these hold:

1. **Open-weight model.** The same model you could run yourself, so results can be reproduced.
2. **No training on your prompts**, stated in the provider's terms.
3. **Zero or short data retention**, turned on in your account where it is a setting.
4. **Region and contract** that suit your organisation (for the ICRC, check with the data protection office first).

Snippets in [configs/models/](../configs/models/):

| Provider | Snippet | What to check |
|---|---|---|
| Infomaniak (Switzerland) | `hosted-infomaniak.yaml` | States it doesn't train on or keep prompts. Swiss hosting |
| Together AI | `hosted-together.yaml` | Turn on zero data retention and turn off training in the account settings |

Keys go in `.env`, named after the provider: `provider: together` reads `TOGETHER_API_KEY`. Check each provider's current terms yourself before sending real data: terms change.

Avoid free tiers whose terms allow training on your prompts.

## Closed models

Closed models such as `gpt-4o-mini` still work: set `llm_name: gpt-4o-mini` with no `base_url`, and `OPENAI_API_KEY` in `.env`. Use them only as a point of comparison, never as the default.

## If a model's output fails to parse

Some servers or models reject the default way of asking for JSON. Try, in this order:

```yaml
llm:
  ...
  structured_output: json_mode         # JSON mode, with the schema added to the prompt
  # structured_output: function_calling
```

Failed calls are recorded as `invalid` in `screening.jsonl` or `answer/trace.jsonl`, and the run continues.
