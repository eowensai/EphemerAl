# Configuration Reference

EphemerAI deployments are configured primarily through environment variables in a `.env` file. Start by copying `.env.example` to `.env`, then edit values for your environment.

- **Main configuration surface:** `.env`
- **Why:** keeps branding, model choices, networking, and runtime tuning deployment-specific without hard-coding source changes.
- **Default behavior:** `.env.example` is privacy-aligned for local/container deployment and should work for most users with minimal edits.

## Normal users vs power users

Most deployments only need a few variables changed:

- **Normal users typically change:** branding (`APP_DISPLAY_NAME`, `APP_SUBTITLE`, `APP_LOGO_PATH`, `APP_EXPORT_TITLE`), app listening settings (`APP_BIND_ADDRESS`, `APP_PORT`), model source and alias (`OLLAMA_MODEL_SOURCE`, `LLM_MODEL_NAME`), context sizing (`OLLAMA_NUM_CTX`, `LLM_CONTEXT_TOKENS`), upload limit (`MAX_UPLOAD_MB`), and sometimes `DEFAULT_UPLOAD_PROMPT`.
- **Power users tune:** request parameters (`LLM_TEMPERATURE`, `LLM_TOP_P`, penalties, retries/timeouts), Ollama concurrency/runtime (`OLLAMA_MAX_QUEUE`, `OLLAMA_MAX_LOADED_MODELS`, `OLLAMA_NUM_PARALLEL`, `OLLAMA_KV_CACHE_TYPE`), Tika memory (`TIKA_JAVA_TOOL_OPTIONS`), and raw API exposure (`OLLAMA_API_BIND`, `OLLAMA_ORIGINS`).

## Important model-setting distinctions

These four options work together but are not interchangeable:

- **`OLLAMA_MODEL_SOURCE`**: upstream Ollama tag to pull/use (for example `qwen3:8b`).
- **`LLM_MODEL_NAME`**: local model alias/tag that the app actually calls (for example `ephemeral-default`).
- **`OLLAMA_NUM_CTX`**: runtime context window baked into that local Ollama alias/profile runtime.
- **`LLM_CONTEXT_TOKENS`**: app-side budgeting hint used to estimate available document context; this is not what pulls/models or bakes runtime alias config by itself.

## Privacy warning for raw Ollama exposure

Exposing raw Ollama on the network is optional and should be deliberate: direct clients bypass EphemerAI UI/session privacy boundaries.

Default Compose keeps raw Ollama internal-only. External/raw access is opt-in via `docker-compose.api.yml`, with `OLLAMA_API_BIND=127.0.0.1` as the safer default bind.

## App bind warning

`APP_BIND_ADDRESS=0.0.0.0` allows the Streamlit app to listen on all interfaces and can make it reachable from other machines on the same network. Use `APP_BIND_ADDRESS=127.0.0.1` for host-local access only.

## `OLLAMA_NO_CLOUD` guidance

`OLLAMA_NO_CLOUD` defaults to `1` and disables Ollama cloud features so deployment behavior remains local-only/privacy-aligned. Do not change this unless you intentionally want Ollama cloud features and understand the privacy implications.

## Environment variables (.env.example)

`MAX_UPLOAD_MB` is the single user-facing upload limit: it is enforced by the app upload guardrails and passed to the Dockerized Streamlit server runtime upload cap. Very large files can still fail due to browser limits, Apache Tika parsing/memory constraints, or model context/token budgeting limits.

| Option | Default | Required? | Valid values/range | What it does | When to change it |
|---|---|---|---|---|---|
| `APP_DISPLAY_NAME` | `EphemerAI` | No | Non-empty string | Main app brand name in UI. | Change for your organization/product branding. |
| `APP_SUBTITLE` | `Privacy-first document chat` | No | String | Short subtitle shown in app chrome. | Update for your use case messaging. |
| `APP_WELCOME_SUBTITLE` | `Upload files and chat locally with your documents.` | No | String | Welcome/empty-state helper text. | Adjust onboarding tone/instructions. |
| `APP_LOGO_PATH` | `static/ephemeral_logo.png` | No | Path to local asset | Path to logo asset served by app. | Change when using custom logo. |
| `APP_EXPORT_TITLE` | `EphemerAI Conversation Export` | No | String | Title used in exported conversations. | Rebrand exports or compliance labeling. |
| `SYSTEM_PROMPT_PATH` | `system_prompt_template.md` | No | Path to readable prompt template file | System prompt template file loaded by app. | Use a custom prompt policy/template. |
| `MAX_UPLOAD_MB` | `50` | No | Positive integer MB (practical range depends on host resources) | Max per-file upload size guardrail in the app and Dockerized Streamlit server runtime. | Raise/lower upload limit for capacity/risk policy. |
| `DEFAULT_UPLOAD_PROMPT` | `Summarize the key points from the uploaded document.` | No | String | Default prompt inserted for document analysis flows. | Change default task framing for users. |
| `EPHEMERAL_DEBUG` | `false` | No | `true`/`false` | Enables debug behavior/log verbosity intended for troubleshooting. | Temporary debugging only. |
| `EPHEMERAL_TIMEZONE` | _(empty)_ | No | IANA timezone (for example `America/New_York`) or empty | Optional timezone override for app behavior that needs timezone context. | Set for deterministic time display/ops behavior. |
| `LLM_BASE_URL` | `http://ollama:11434/v1` | Yes (unless app default matches environment) | URL to OpenAI-compatible LLM endpoint | Endpoint the app uses for chat completions. | Point app to external or differently routed LLM service. |
| `LLM_MODEL_NAME` | `ephemeral-default` | Yes | Existing local Ollama model tag/alias | Model name the app requests on each call. | Switch model family or local alias target. |
| `LLM_CONTEXT_TOKENS` | `32768` | No | Positive integer tokens | App-side context size hint for budgeting docs/history. | Match your runtime context strategy. |
| `LLM_OUTPUT_RESERVE_TOKENS` | `32768` | No | Non-negative integer tokens (typically less than/equal to context) | Reserved headroom for model output during budgeting. | Tune tradeoff between doc fit and reply headroom. |
| `LLM_REQUEST_TIMEOUT_S` | `1800` | No | Positive integer seconds | Request timeout for LLM API calls. | Increase for slow hardware/large prompts. |
| `LLM_MAX_RETRIES` | `0` | No | Integer `0+` | API retry count for failed LLM requests. | Increase if transient failures are common. |
| `LLM_TEMPERATURE` | `0.7` | No | Float usually `0.0–2.0` (model-dependent) | Sampling randomness for responses. | Lower for determinism, raise for creativity. |
| `LLM_TOP_P` | `0.8` | No | Float `0.0–1.0` | Nucleus sampling control. | Tune output diversity/stability. |
| `LLM_PRESENCE_PENALTY` | `1.5` | No | Float (commonly `-2.0–2.0`, provider-dependent) | Penalizes repeated topical presence. | Reduce repetition or encourage topic shifts. |
| `LLM_REASONING_EFFORT` | `none` | No | Provider/model-supported values (for Ollama/OpenAI-compatible often `none`/`low`/`medium`/`high`) | Requests reasoning effort tier where supported. | Enable/tune explicit reasoning modes. |
| `LLM_THINKING_EFFORT` | _(empty)_ | No | Provider/model-supported string or empty | Alternate/extra effort hint for models exposing “thinking” controls; blank resolves to the app default `high` when Thinking Mode is enabled. | Only when using models that honor this knob. |
| `LLM_SHOW_REASONING` | `false` | No | `true`/`false` | Controls whether reasoning/thought output is surfaced when available. | Debugging or specialized UX needs. |
| `LLM_MAX_TOKENS` | _(empty)_ | No | Empty or positive integer | Optional output token cap for model responses. | Enforce bounded response length/cost. |
| `LLM_SUPPORTS_VISION` | _(empty)_ | No | Empty/whitespace = auto-detect; truthy: `1,true,yes,y,on`; falsy: `0,false,no,n,off` | Optional capability hint for image support. | Force/override detection edge cases while keeping blank as auto-detect. |
| `IMG_TOKEN_COST_DEFAULT` | `1024` | No | Positive integer estimated tokens/image | Budgeting estimate per image attachment. | Calibrate budgeting for your model behavior. |
| `ENABLE_TOKEN_BUDGETING` | `true` | No | `true`/`false` | Enables app-side context budgeting safeguards. | Disable only for controlled experiments. |
| `TIKA_URL` | `http://tika-server:9998` | Yes (unless app default matches environment) | URL to Apache Tika server | Document parsing backend endpoint. | Point to external Tika or different network path. |
| `TIKA_TIMEOUT_S` | `120` | No | Positive integer seconds | Timeout for document parsing requests. | Increase for large/complex documents. |
| `OLLAMA_API_BIND` | `127.0.0.1` | No | Bind address/IP | Bind used when intentionally exposing raw Ollama via compose override. | Change only when deliberately sharing raw API. |
| `OLLAMA_ORIGINS` | _(empty)_ | No | Comma-separated origins or empty | Allowed origins for Ollama API/CORS behavior. | Required for browser-based external clients. |
| `OLLAMA_NO_CLOUD` | `1` | No | `0` or `1` | Disables Ollama cloud features when `1`. | Change only if intentionally enabling cloud features. |
| `OLLAMA_MAX_QUEUE` | `16` | No | Positive integer | Max queued inference requests in Ollama. | Tune under multi-user load. |
| `OLLAMA_MAX_LOADED_MODELS` | `1` | No | Positive integer | Max concurrently loaded models in Ollama memory. | Raise only with enough RAM/VRAM. |
| `OLLAMA_NUM_PARALLEL` | `1` | No | Positive integer | Parallel request execution slots in Ollama. | Increase for concurrency after benchmarking. |
| `OLLAMA_KEEP_ALIVE` | `-1` | No | Integer seconds or `-1` (implementation-dependent semantics) | Model unload/keepalive behavior between requests. | Tune cold-start vs memory retention. |
| `OLLAMA_FLASH_ATTENTION` | `1` | No | `0` or `1` | Enables Flash Attention optimizations where supported. | Disable for compatibility troubleshooting. |
| `OLLAMA_KV_CACHE_TYPE` | `f16` | No | Ollama-supported cache types (for example `f16`, `q8_0`; support varies by build/hardware) | KV cache precision/compression setting. | Tune memory usage vs quality/perf. |
| `OLLAMA_FORCE_CUBLAS_LT` | `1` | No | `0` or `1` | Forces cuBLASLt path on supported NVIDIA setups. | Disable only if encountering backend issues. |
| `OLLAMA_MODEL_SOURCE` | `qwen3:8b` | Yes for profile/bootstrap workflows | Valid Ollama model tag | Upstream model tag pulled/used to build local alias. | Retarget deployment model family/size. |
| `OLLAMA_NUM_CTX` | `32768` | No | Positive integer tokens (bounded by model/runtime/hardware limits) | Runtime context window for Ollama model profile/alias. | Increase/decrease based on VRAM and use case. |
| `OLLAMA_NUM_PREDICT` | `-1` | No | Integer (`-1` for unlimited/default behavior, otherwise positive cap) | Default generation length behavior at Ollama runtime layer. | Cap outputs globally at runtime layer. |
| `OLLAMA_TEMPERATURE` | `0.7` | No | Float usually `0.0–2.0` | Ollama-side default temperature for alias/runtime profile. | Align runtime defaults with desired style. |
| `OLLAMA_TOP_P` | `0.8` | No | Float `0.0–1.0` | Ollama-side nucleus sampling default. | Tune diversity at runtime profile layer. |
| `OLLAMA_TOP_K` | `40` | No | Positive integer | Ollama-side top-k sampling default. | Adjust token selection sharpness. |
| `OLLAMA_MIN_P` | `0.0` | No | Float `0.0–1.0` | Ollama-side minimum-probability sampling threshold. | Prune unlikely tokens for stability/speed. |
| `OLLAMA_REPEAT_PENALTY` | `1.1` | No | Positive float (commonly around `0.8–2.0`) | Ollama-side repetition penalty. | Reduce loops/repetition artifacts. |
| `TIKA_JAVA_TOOL_OPTIONS` | `-Xmx2g -Xms512m` | No | Java options string | JVM memory/runtime flags for Tika container. | Increase heap or tune GC for heavy docs. |
| `APP_BIND_ADDRESS` | `0.0.0.0` | No | Valid bind host/IP | Streamlit server bind address. | Lock to localhost or expose on LAN. |
| `APP_PORT` | `8501` | No | Valid TCP port `1–65535` | Streamlit server listening port. | Change to avoid port conflicts/policy needs. |
