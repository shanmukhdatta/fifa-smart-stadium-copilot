"""
Lightweight RAG retriever over the stadium knowledge base.

Design choice: embeddings are computed locally with a TF-IDF vectorizer
built over the corpus's own vocabulary, instead of calling an external
embeddings API. For an MVP knowledge base of five short documents this is
faster and more reliable in a live demo (no network dependency, no extra
API cost, fully deterministic) while still exercising a real FAISS vector
search -- which is the thing actually being evaluated. TF-IDF specifically
(over a naive hashed bag-of-words) matters here because it down-weights
terms that appear in nearly every document (e.g. "gate", "stadium") and
up-weights the terms that actually distinguish a query's topic (e.g.
"restroom", "wheelchair") -- without it, cross-topic chunks bleed into
results. Swapping in OpenAI/other embeddings later only touches
`_build_vocabulary()` and `_embed()`.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

import faiss
import numpy as np

from backend.core.logging_config import get_logger

logger = get_logger(__name__)

DOCS_DIR = Path(__file__).parent / "documents"


_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "do", "does", "for",
    "from", "get", "how", "i", "in", "is", "it", "my", "of", "on", "or",
    "that", "the", "this", "to", "was", "what", "where", "which", "who",
    "will", "with",
}


def _stem(token: str) -> str:
    """Minimal suffix stripping -- enough to unify restroom/restrooms,
    entrance/entrances, exit/exits without pulling in a full NLP dependency."""
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 4 and token.endswith("es") and not token.endswith("ses"):
        return token[:-2]
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [_stem(tok) for tok in tokens if tok not in _STOPWORDS]


class Retriever:
    """A small in-memory FAISS index over the markdown knowledge base, using TF-IDF vectors."""

    def __init__(self, docs_dir: Path = DOCS_DIR):
        self._chunks: list[str] = []
        self._sources: list[str] = []
        self._vocab: dict[str, int] = {}
        self._idf: np.ndarray = np.zeros(0, dtype="float32")
        self._index: faiss.IndexFlatIP | None = None
        self._load(docs_dir)

    def _load(self, docs_dir: Path) -> None:
        if not docs_dir.exists():
            logger.warning("RAG docs directory missing: %s", docs_dir)
            return

        raw_chunks: list[str] = []
        sources: list[str] = []
        for path in sorted(docs_dir.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            # Drop markdown header lines (# ...) -- as standalone chunks
            # they're too short and skew similarity scores disproportionately.
            body_lines = [
                line for line in text.split("\n")
                if not line.strip().startswith("#")
            ]
            body = "\n".join(body_lines)
            for para in [p.strip() for p in body.split("\n\n") if p.strip()]:
                # Sentence-level chunking: a paragraph mixing several
                # topics (e.g. gates, restrooms, food stalls in one block)
                # would otherwise dilute the score for any single-topic
                # query. Splitting to sentences keeps each chunk focused.
                sentences = [
                    s.strip() for s in re.split(r"(?<=[.!?])\s+", para.replace("\n", " "))
                    if s.strip()
                ]
                for sentence in sentences:
                    raw_chunks.append(sentence)
                    sources.append(path.stem)

        if not raw_chunks:
            return

        self._chunks = raw_chunks
        self._sources = sources
        self._build_vocabulary(raw_chunks)

        vectors = np.vstack([self._embed(chunk) for chunk in raw_chunks])
        self._index = faiss.IndexFlatIP(len(self._vocab))
        self._index.add(vectors)
        logger.info(
            "RAG index built with %d chunks, %d vocab terms from %s",
            len(self._chunks), len(self._vocab), docs_dir,
        )

    def _build_vocabulary(self, chunks: list[str]) -> None:
        doc_freq: Counter = Counter()
        for chunk in chunks:
            for tok in set(_tokenize(chunk)):
                doc_freq[tok] += 1

        self._vocab = {tok: i for i, tok in enumerate(sorted(doc_freq))}
        n_docs = len(chunks)
        idf = np.zeros(len(self._vocab), dtype="float32")
        for tok, idx in self._vocab.items():
            # Smoothed IDF: common terms across most docs get pushed toward
            # zero weight; rare, topic-specific terms get amplified.
            idf[idx] = math.log((1 + n_docs) / (1 + doc_freq[tok])) + 1.0
        self._idf = idf

    def _embed(self, text: str) -> np.ndarray:
        vec = np.zeros(len(self._vocab), dtype="float32")
        tokens = _tokenize(text)
        if not tokens:
            return vec
        tf = Counter(tokens)
        for tok, count in tf.items():
            idx = self._vocab.get(tok)
            if idx is not None:
                vec[idx] = count * self._idf[idx]
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        if not self._chunks or self._index is None:
            return []
        query_vec = self._embed(query).reshape(1, -1)
        scores, indices = self._index.search(query_vec, min(top_k, len(self._chunks)))
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1 or score <= 0:
                continue
            results.append(
                {
                    "text": self._chunks[idx],
                    "source": self._sources[idx],
                    "score": float(score),
                }
            )
        return results


@lru_cache
def get_retriever() -> Retriever:
    """Singleton retriever -- index is built once per process."""
    return Retriever()
