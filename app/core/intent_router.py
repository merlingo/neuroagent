class IntentRouter:
    def route(self, text: str) -> str:
        lowered = text.lower()
        if "sigma" in lowered or "threat" in lowered:
            return "cybersecurity"
        if "investor" in lowered or "gtm" in lowered:
            return "investor_gtm"
        if "weekly" in lowered or "focus" in lowered:
            return "productivity"
        return "research"
