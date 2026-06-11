import yaml


def validate_yaml(payload: dict) -> dict:
    content = payload.get("content", payload.get("sigma_rule", ""))
    try:
        parsed = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        return {"valid": False, "error": str(exc)}
    if not isinstance(parsed, dict):
        return {"valid": False, "error": "Sigma content must parse to an object"}
    missing = [field for field in ["title", "logsource", "detection"] if field not in parsed]
    return {
        "valid": not missing,
        "missing_fields": missing,
        "status": "validated" if not missing else "invalid",
    }
