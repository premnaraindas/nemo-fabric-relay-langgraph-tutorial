"""NeMo Fabric adapter for the support agent: start, invoke, stream, stop."""
import json
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import nemo_relay
from langchain_openai import ChatOpenAI
from nemo_fabric_adapter_contract.models import AgentConfig, AgentRunError, AgentRunResult, AgentRunStatus
from nemo_fabric_adapters.common import lifecycle, utils
from nemo_relay.integrations.langgraph import NemoRelayMiddleware, configure_graph

from support_agent import agent


def no_deletes(tool_name, args):
    """Relay guardrail: return a message to block a tool call, None to allow it."""
    if tool_name == "delete_customer":
        return "Policy: customer records cannot be deleted by an agent."
    return None


nemo_relay.guardrails.register_tool_conditional_execution("no_deletes", 10, no_deletes)


def result(text, error=None):
    """Build the normalized result NeMo Fabric returns to the caller."""
    if error is None:
        return AgentRunResult(status=AgentRunStatus.SUCCEEDED, output={"response": text, "deleted": list(agent.DELETED)})
    if "guardrail rejected" not in str(error):
        raise error
    return AgentRunResult(status=AgentRunStatus.FAILED, output={"response": text, "deleted": list(agent.DELETED)},
                          error=AgentRunError(code="guardrail_rejected", message=str(error)))


class SupportRuntime:
    async def start(self, payload):
        model = payload["config"].models["default"]
        llm = ChatOpenAI(model=model.model, base_url=model.base_url, temperature=model.temperature or 0,
                         api_key=os.environ.get(model.api_key_env or "", "none"), streaming=True)
        self._graph = configure_graph(agent.build_agent(llm, middleware=[NemoRelayMiddleware()]))
        self._model = model.model
        self._base_dir = str(Path(payload.get("base_dir") or ".").resolve())

    @asynccontextmanager
    async def _relay(self, context):
        """Turn Relay on for one call when the Fabric config enabled it."""
        telemetry = context.telemetry
        if telemetry is None or not telemetry.relay_enabled:
            yield
            return
        plugins = json.loads(Path(telemetry.config_path).read_text())["relay"]["config"]
        utils.normalize_relay_output_dirs(plugins, {
            "agent_name": "support-agent", "base_dir": self._base_dir,
            "config": {"models": {"default": {"model": self._model}}}, "runtime_context": context.to_mapping()})
        async with nemo_relay.plugin.activate(plugins):
            request_context, metadata = utils.relay_request_context(context.request_id)
            with request_context, nemo_relay.scope.scope("support-agent", nemo_relay.ScopeType.Agent, metadata=metadata):
                yield

    async def invoke(self, request, context):
        try:
            async with self._relay(context):
                state = await self._graph.ainvoke({"messages": [("user", request.input)]})
        except RuntimeError as error:
            return result("", error)
        return result(state["messages"][-1].content)

    async def invoke_openai_stream(self, request, context, emit):
        completion_id, created, text = "chatcmpl-" + uuid.uuid4().hex, int(time.time()), []

        def chunk(delta, finish_reason=None):
            return {"id": completion_id, "object": "chat.completion.chunk", "created": created, "model": self._model,
                    "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}]}

        try:
            async with self._relay(context):
                async for message, _ in self._graph.astream({"messages": [("user", request.input)]}, stream_mode="messages"):
                    if type(message).__name__ == "AIMessageChunk" and isinstance(message.content, str) and message.content:
                        text.append(message.content)
                        await emit(chunk({"content": message.content}))
        except RuntimeError as error:
            return result("".join(text), error)
        await emit(chunk({}, "stop"))
        return result("".join(text))

    async def stop(self):
        self._graph = None


def main():
    lifecycle.serve(SupportRuntime, config_loader=AgentConfig.from_mapping)


if __name__ == "__main__":
    main()
