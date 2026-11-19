# Run a LangGraph agent on NVIDIA NeMo Fabric, with tracing and guardrails from NeMo Relay

A small, complete sample: one support agent with two tools, moved from NVIDIA NeMo Agent Toolkit to plain LangGraph, wrapped in a NeMo Fabric adapter, with NeMo Relay tracing, a tool guardrail and email redaction.

NVIDIA deprecated NeMo Agent Toolkit in October 2026, with end of life by the end of 2026. See the [migration guide](https://docs.nvidia.com/nemo/agent-toolkit/latest/resources/migration-guide.html).

## What is here

| Path | What it is |
| --- | --- |
| `before/` | The starting point: the same agent as a NeMo Agent Toolkit workflow |
| `support_agent/agent.py` | The agent as plain LangChain and LangGraph |
| `support_agent/support.fabric-adapter.json` | The NeMo Fabric adapter descriptor |
| `support_agent/adapter.py` | The adapter runtime: start, invoke, stream, stop, with NeMo Relay |
| `run.py` | Plans, runs and streams the agent through NeMo Fabric |
| `check_events.py` | Summarizes the NeMo Relay event files after a run |

## Run it

Tested on Ubuntu 24.04 with Python 3.12, NeMo Fabric 0.6.1 and NeMo Relay 0.11.1. It also ran unchanged on NeMo Fabric 0.7.0rc1.

```bash
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python -r requirements.txt

export MODEL=<model id>
export MODEL_BASE_URL=<OpenAI-compatible base URL, ending in /v1>
export MODEL_API_KEY=<your key>

.venv/bin/python run.py            # Fabric only
.venv/bin/python run.py --relay    # Fabric with Relay tracing, a guardrail and redaction
.venv/bin/python check_events.py   # count events and redactions
```

Any OpenAI-compatible endpoint with a tool-calling model works. We used an NVIDIA Nemotron model.

Expected with `--relay`: the lookup succeeds, the answer streams in chunks, and the delete request fails with `guardrail_rejected` while `deleted` stays empty. The trace is under `artifacts/relay/`, with email addresses replaced by `[REDACTED]`.

## The starting point

```bash
cd before
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python -e .
.venv/bin/nat run --config_file workflow.yml --input "Which plan is jane.doe@example.com on?"
```

## Notes

- If the virtual environment is not activated, NeMo Fabric 0.6.1 can start the adapter host under the system `python3`. `run.py` sets `ADAPTER_PYTHON` to avoid this. See [NeMo-Fabric issue 635](https://github.com/NVIDIA/NeMo-Fabric/issues/635).
- Guardrail names are process-wide. Register a guardrail once, at module load.
- Redaction applies to exported telemetry. The user and the model still see real values.
- One invocation at a time per runtime.
- The adapter contract is `fabric.adapter/v1alpha2`, an alpha contract.

## License

Apache 2.0. This is an independent sample and is not an NVIDIA product.
