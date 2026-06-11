from app.rag.ingestion import DocumentIngestor


def main() -> None:
    ingestor = DocumentIngestor()
    result = ingestor.ingest("Demo", "NeuroAgent ingestion demo.", {"source_type": "local"})
    print(result)


if __name__ == "__main__":
    main()
