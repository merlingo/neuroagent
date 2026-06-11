def requires_approval(action: str) -> bool:
    return action in {"email.send", "production.deploy_rule", "shell.execute", "file.delete"}
