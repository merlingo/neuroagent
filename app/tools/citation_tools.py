def verify(payload: dict) -> dict:
    citations = payload.get("citations", [])
    if not citations and payload.get("url"):
        citations = [{"url": payload["url"]}]
    checked = []
    for citation in citations:
        url = citation.get("url") or citation.get("source_uri") or ""
        checked.append(
            {
                "url": url,
                "valid": url.startswith(("http://", "https://", "file://", "obsidian://")),
                "reason": "recognized URI scheme" if url else "missing URI",
            }
        )
    return {
        "status": "verified",
        "valid": all(item["valid"] for item in checked) if checked else False,
        "citations": checked,
    }
