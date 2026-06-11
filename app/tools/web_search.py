def search(payload: dict) -> dict:
    query = payload.get("query", "")
    limit = int(payload.get("limit", 5))
    results = []
    if query:
        results.append(
            {
                "title": f"Stub search result for {query}",
                "url": payload.get("source_url", "https://example.com/stub-search-result"),
                "snippet": f"Deterministic offline search stub for query: {query}",
            }
        )
    return {"status": "stubbed", "query": query, "results": results[:limit]}
