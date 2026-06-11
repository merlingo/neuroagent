from typing import Any

from app.contracts.agent_contract import JsonSchema
from app.core.errors import ContractValidationError


PYTHON_TYPES: dict[str, type | tuple[type, ...]] = {
    "string": str,
    "number": (int, float),
    "integer": int,
    "boolean": bool,
    "object": dict,
    "array": list,
}


def validate_payload(schema: JsonSchema, payload: dict[str, Any], label: str) -> None:
    if schema.type != "object":
        raise ContractValidationError(f"{label} schema type must be object")

    missing = [field for field in schema.required if field not in payload]
    if missing:
        raise ContractValidationError(f"{label} missing required fields: {', '.join(missing)}")

    for field, field_schema in schema.properties.items():
        if field not in payload:
            continue
        expected_type = field_schema.get("type")
        if expected_type is None:
            continue
        python_type = PYTHON_TYPES.get(expected_type)
        if python_type is None:
            continue
        if expected_type in {"integer", "number"} and isinstance(payload[field], bool):
            raise ContractValidationError(f"{label}.{field} must be {expected_type}")
        if not isinstance(payload[field], python_type):
            raise ContractValidationError(f"{label}.{field} must be {expected_type}")
