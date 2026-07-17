from backend.ai.rag.retriever import get_retriever


def test_retriever_loads_documents():
    retriever = get_retriever()
    assert len(retriever._chunks) > 0


def test_retriever_returns_relevant_chunk_for_wheelchair_query():
    retriever = get_retriever()
    results = retriever.search("wheelchair accessible entrance", top_k=3)
    assert len(results) > 0
    combined = " ".join(r["text"].lower() for r in results)
    assert "wheelchair" in combined or "accessible" in combined


def test_retriever_handles_empty_index_gracefully(tmp_path):
    from backend.ai.rag.retriever import Retriever

    empty_retriever = Retriever(docs_dir=tmp_path)
    assert empty_retriever.search("anything") == []
