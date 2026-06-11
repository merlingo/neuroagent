from app.rag.ingestion import DocumentIngestor
from app.rag.retriever import InMemoryRetriever


def test_rag_ingest_and_search() -> None:
    ingestor = DocumentIngestor()
    ingestor.ingest("Sigma", "Sigma rules can represent behavioral threat vectors.", {})
    results = InMemoryRetriever(ingestor).search("behavioral threat")
    assert results
    assert results[0]["citation_id"].startswith("cite:")
