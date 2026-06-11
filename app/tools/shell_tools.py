def request_shell_approval(payload: dict) -> dict:
    return {
        "status": "approval_required",
        "command": payload.get("command", ""),
        "message": "shell.execute is high-risk and must be executed through ToolExecutor approval flow.",
    }
