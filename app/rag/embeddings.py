class MockEmbeddingProvider:
    def embed(self, text: str) -> list[float]:
        return [float((sum(text.encode("utf-8")) % 997) / 997)]
