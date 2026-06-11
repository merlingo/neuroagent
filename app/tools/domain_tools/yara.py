def validate_rule(payload: dict) -> dict:
    content = payload.get("content", payload.get("rule", ""))
    valid = "rule " in content and "condition:" in content
    return {
        "valid": valid,
        "status": "validated" if valid else "invalid",
        "error": None if valid else "YARA rule must contain a rule declaration and condition block",
    }
