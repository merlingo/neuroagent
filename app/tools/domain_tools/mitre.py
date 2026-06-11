def lookup(payload: dict) -> dict:
    technique = payload.get("technique") or payload.get("technique_id") or payload.get("query") or "unknown"
    catalog = {
        "T1059": {
            "technique_id": "T1059",
            "name": "Command and Scripting Interpreter",
            "tactic": "Execution",
        },
        "T1003": {
            "technique_id": "T1003",
            "name": "OS Credential Dumping",
            "tactic": "Credential Access",
        },
    }
    match = catalog.get(str(technique).upper())
    return {
        "status": "stubbed",
        "query": technique,
        "match": match,
        "found": match is not None,
    }
