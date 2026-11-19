"""The support agent's two tools as NeMo Agent Toolkit functions (the starting point)."""
import json

from nat.builder.builder import Builder
from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.function import FunctionBaseConfig


class LookupCustomerConfig(FunctionBaseConfig, name="lookup_customer"):
    pass


@register_function(config_type=LookupCustomerConfig)
async def lookup_customer(config: LookupCustomerConfig, builder: Builder):
    async def _lookup(email: str) -> str:
        return json.dumps({"email": email, "plan": "Enterprise", "seats": 40, "contact": "billing.owner@example.com"})

    yield FunctionInfo.from_fn(_lookup, description="Look up a customer record by email address.")


class DeleteCustomerConfig(FunctionBaseConfig, name="delete_customer"):
    pass


@register_function(config_type=DeleteCustomerConfig)
async def delete_customer(config: DeleteCustomerConfig, builder: Builder):
    async def _delete(email: str) -> str:
        return "deleted"

    yield FunctionInfo.from_fn(_delete, description="Permanently delete a customer record by email address.")
