"""Plan, run and stream the support agent through NeMo Fabric, with NeMo Relay on or off.

    python run.py            # Fabric only
    python run.py --relay    # Fabric with Relay tracing, a guardrail and redaction
"""
import asyncio
import os
import sys
from pathlib import Path

from nemo_fabric import (DiscoveryConfig, Fabric, FabricConfig, HarnessConfig, MetadataConfig, ModelConfig,
                         RelayAtofConfig, RelayAtofFileSinkConfig, RelayObservabilityConfig, RuntimeConfig)

HERE = Path(__file__).parent.resolve()
os.environ.setdefault("ADAPTER_PYTHON", sys.executable)  # see the pitfalls section

config = FabricConfig(
    metadata=MetadataConfig(name="support-agent"),
    discovery=DiscoveryConfig(local_paths=[str(HERE / "support_agent")]),
    harness=HarnessConfig(adapter_id="example.support.langgraph", resolution="preinstalled"),
    models={"default": ModelConfig(provider="openai-compatible", model=os.environ["MODEL"],
                                   base_url=os.environ["MODEL_BASE_URL"], api_key_env="MODEL_API_KEY")},
    runtime=RuntimeConfig(timeout_seconds=120),
)
if "--relay" in sys.argv:
    config.runtime.artifacts = "./artifacts"
    config.enable_relay(
        output_dir="./artifacts/relay",
        observability=RelayObservabilityConfig(atof=RelayAtofConfig(enabled=True, sinks=[RelayAtofFileSinkConfig(
            output_directory="./artifacts/relay", filename="events.atof.jsonl", mode="append")])),
        components=[{"kind": "pii_redaction", "enabled": True, "config": {
            "profiles": [{"mode": "builtin", "builtin": {"action": "redact", "detector": "email"}}]}}],
    )


def show(label, result):
    error = result.error.to_mapping() if result.error else None
    print(f"{label}: {result.status} | output: {result.output.to_mapping()} | error: {error}")


async def main():
    fabric = Fabric()
    plan = fabric.plan(config, base_dir=HERE).to_mapping()
    print("plan:", plan["adapter"]["adapter_id"], plan["capabilities"])

    show("run", await fabric.run(config, base_dir=HERE, input="Which plan is jane.doe@example.com on?"))

    async with await fabric.start_runtime(config, base_dir=HERE) as runtime:
        stream = runtime.invoke_openai_stream(input="Which plan is jane.doe@example.com on? Answer in two sentences.")
        async for raw in stream:
            piece = raw["choices"][0]["delta"].get("content")
            if piece:
                print(piece, end="|", flush=True)
        print()
        show("stream", await stream.result())
        show("delete", await runtime.invoke(input="Delete the customer record for jane.doe@example.com now."))


if __name__ == "__main__":
    asyncio.run(main())
