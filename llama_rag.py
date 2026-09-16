"""Private, local LlamaIndex retrieval for Exam Saathi uploads.

The answer model is deliberately kept outside this module.  LlamaIndex only
ingests uploaded notes, preserves their source metadata and retrieves evidence.
If this optional layer is disabled or unavailable, callers fall back to Exam
Saathi's proven semantic/TF-IDF retriever.
"""

from __future__ import annotations

import os
from typing import Any

from sklearn.feature_extraction.text import HashingVectorizer


def _truthy(name: str, default: str = "true") -> bool:
    return os.environ.get(name, default).strip().casefold() in {"1", "true", "yes", "on"}


class LlamaIndexUnavailable(RuntimeError):
    """Raised when the optional LlamaIndex path cannot safely run."""


def is_enabled() -> bool:
    return _truthy("EXAM_SAATHI_LLAMA_INDEX", "true")


def _normalise_metadata(chunk: dict[str, Any], position: int) -> dict[str, Any]:
    return {
        "source_name": str(chunk.get("source_name") or "Uploaded material"),
        "page_number": int(chunk.get("page_number") or 1),
        "source_type": str(chunk.get("source_type") or "Uploaded document"),
        "document_id": str(chunk.get("document_id") or ""),
        "original_chunk": int(chunk.get("chunk_id") or position),
    }


def retrieve_with_llamaindex(
    query: str,
    chunks: list[dict[str, Any]],
    top_k: int = 6,
) -> list[dict[str, Any]]:
    """Retrieve upload evidence through an ephemeral in-memory LlamaIndex.

    A stateless hashing embedding keeps this route free, local and multilingual
    friendly.  Nothing is written to disk or sent to a third-party embedding
    service.  The index lives only for the current request.
    """
    if not is_enabled():
        raise LlamaIndexUnavailable("LlamaIndex retrieval is disabled by configuration.")
    query = (query or "").strip()
    if not query:
        raise ValueError("Search query cannot be empty.")
    if not chunks:
        return []

    try:
        from llama_index.core import Document, VectorStoreIndex
        from llama_index.core.embeddings import BaseEmbedding
        from llama_index.core.ingestion import IngestionPipeline
        from llama_index.core.node_parser import SentenceSplitter
        from llama_index.core.schema import MetadataMode
    except Exception as error:  # pragma: no cover - exercised by deployment fallback
        raise LlamaIndexUnavailable(f"LlamaIndex import failed: {error}") from error

    class LocalHashEmbedding(BaseEmbedding):
        """Fixed-size local embedding compatible with LlamaIndex VectorStoreIndex."""

        dimensions: int = 768

        def _vectors(self, texts: list[str]) -> list[list[float]]:
            vectorizer = HashingVectorizer(
                analyzer="char_wb",
                ngram_range=(3, 5),
                n_features=self.dimensions,
                alternate_sign=False,
                norm="l2",
                lowercase=True,
            )
            matrix = vectorizer.transform(texts)
            return matrix.toarray().astype(float).tolist()

        def _get_query_embedding(self, query: str) -> list[float]:
            return self._vectors([query])[0]

        def _get_text_embedding(self, text: str) -> list[float]:
            return self._vectors([text])[0]

        def _get_text_embeddings(self, texts: list[str]) -> list[list[float]]:
            return self._vectors(texts)

        async def _aget_query_embedding(self, query: str) -> list[float]:
            return self._get_query_embedding(query)

        async def _aget_text_embedding(self, text: str) -> list[float]:
            return self._get_text_embedding(text)

    documents = []
    for position, chunk in enumerate(chunks, start=1):
        text = str(chunk.get("text") or "").strip()
        if text:
            documents.append(
                Document(
                    text=text,
                    metadata=_normalise_metadata(chunk, position),
                    id_=f"upload-{position}",
                )
            )
    if not documents:
        return []

    chunk_size = max(128, min(1024, int(os.environ.get("LLAMA_INDEX_CHUNK_SIZE", "512"))))
    overlap = max(0, min(chunk_size // 3, int(os.environ.get("LLAMA_INDEX_CHUNK_OVERLAP", "64"))))
    pipeline = IngestionPipeline(
        transformations=[SentenceSplitter(chunk_size=chunk_size, chunk_overlap=overlap)]
    )
    nodes = pipeline.run(documents=documents, show_progress=False)
    if not nodes:
        return []

    embed_model = LocalHashEmbedding(model_name="exam-saathi-local-hash-v1")
    index = VectorStoreIndex(nodes=nodes, embed_model=embed_model, show_progress=False)
    retriever = index.as_retriever(similarity_top_k=min(max(1, top_k), len(nodes)))
    matches = retriever.retrieve(query)

    results: list[dict[str, Any]] = []
    seen: set[tuple[str, int, str]] = set()
    for ranked, match in enumerate(matches, start=1):
        node = match.node
        metadata = dict(node.metadata or {})
        text = node.get_content(metadata_mode=MetadataMode.NONE).strip()
        source_name = str(metadata.get("source_name") or "Uploaded material")
        page_number = int(metadata.get("page_number") or 1)
        dedupe_key = (source_name, page_number, text)
        if not text or dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        results.append({
            "rank": ranked,
            "score": round(float(match.score or 0.0), 4),
            "text": text,
            "source_name": source_name,
            "page_number": page_number,
            "source_type": str(metadata.get("source_type") or "Uploaded document"),
            "retrieval_engine": "LlamaIndex local vector index",
        })
    return results

