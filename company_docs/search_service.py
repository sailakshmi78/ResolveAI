import threading
import time
import re
from django.db.models import Count, Max

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from company_docs.models import DocumentChunk


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

_model = None
_model_lock = threading.Lock()

_index = None
_cached_chunks = []
_cached_signature = None
_index_lock = threading.Lock()


def get_model():
    """Load the local embedding model once per Python process."""
    global _model

    if _model is None:
        with _model_lock:
            if _model is None:
                _model = SentenceTransformer(
                    MODEL_NAME,
                    local_files_only=True,
                )

    return _model


def get_search_index():
    """Reuse FAISS until active chunk content or metadata changes."""
    global _index, _cached_chunks, _cached_signature

    active_chunks = DocumentChunk.objects.filter(document__is_active=True)
    stats = active_chunks.aggregate(
        chunk_count=Count("id"),
        max_chunk_id=Max("id"),
        max_chunk_index=Max("chunk_index"),
        latest_document_update=Max("document__updated_at"),
    )
    signature = (
        stats["chunk_count"],
        stats["max_chunk_id"],
        stats["max_chunk_index"],
        stats["latest_document_update"],
    )

    # Avoid materializing every chunk's full text on every request. The active
    # document timestamp invalidates the cache when handbook ingestion updates it.
    if not stats["chunk_count"]:
        with _index_lock:
            _index = None
            _cached_chunks = []
            _cached_signature = None
        return None, [], None

    if _index is not None and signature == _cached_signature:
        return _index, _cached_chunks, get_model()

    with _index_lock:
        if _index is not None and signature == _cached_signature:
            return _index, _cached_chunks, get_model()

        chunks = list(
            active_chunks.select_related("document")
            .order_by("document_id", "chunk_index")
        )
        model = get_model()
        texts = [chunk.content for chunk in chunks]

        embeddings = model.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        ).astype("float32")

        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings)

        _index = index
        _cached_chunks = chunks
        _cached_signature = signature

        return _index, _cached_chunks, model


def _guidance_terms(text):
    """Normalize useful query and passage terms for lexical evidence checks."""
    stopwords = {
        "a", "an", "and", "are", "as", "at", "be", "by", "can",
        "do", "does", "for", "from", "how", "i", "if", "in",
        "is", "it", "me", "my", "of", "on", "or", "should",
        "the", "their", "they", "this", "to", "what", "when",
        "where", "which", "who", "why", "will", "with", "would",
        "you", "your", "company", "employee", "employees",
        "work", "policy", "policies", "please", "tell", "about",
        "exact", "new"
    }

    synonyms = {
        "procedure": "process",
        "procedures": "process",
        "workflow": "process",
        "workflows": "process",
        "requesting": "request",
        "requested": "request",
        "requests": "request",
        "laptops": "laptop",
        "devices": "device",
        "configuration": "configure",
        "configuring": "configure",
        "configured": "configure",
        "resolved": "resolution",
        "resolving": "resolution",
        "issues": "issue",
        "reported": "report",
        "reporting": "report",
    }

    terms = re.findall(r"[a-z0-9]+", (text or "").lower())

    return {
        synonyms.get(term, term)
        for term in terms
        if term not in stopwords and len(term) > 1
    }


def search_company_docs(query, top_k=5):
    """Search handbook chunks using semantic similarity and keyword evidence."""
    if not isinstance(query, str) or not query.strip():
        return []

    query_terms = _guidance_terms(query)
    if not query_terms:
        return []

    started = time.perf_counter()
    index, chunks, model = get_search_index()
    print(
        f"[Search] Index/database preparation: "
        f"{time.perf_counter() - started:.2f}s"
    )

    if index is None or not chunks:
        return []

    started = time.perf_counter()
    query_vector = model.encode(
        [query.strip()],
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    ).astype("float32")
    print(f"[Search] Query embedding: {time.perf_counter() - started:.2f}s")

    requested_k = min(max(1, int(top_k)), len(chunks))
    candidate_k = min(max(requested_k * 4, 20), len(chunks))

    scores, positions = index.search(query_vector, candidate_k)

    results = []
    seen_content = set()

    for score, position in zip(scores[0], positions[0]):
        score = float(score)

        if position < 0 or score < 0.30:
            continue

        chunk = chunks[int(position)]
        content = chunk.content or ""
        normalized_content = " ".join(content.lower().split())

        if not normalized_content or normalized_content in seen_content:
            continue

        passage_terms = _guidance_terms(content)
        overlap = query_terms.intersection(passage_terms)

        coverage = len(overlap) / len(query_terms)

        # Require actual topic evidence, not semantic similarity alone.
        if len(query_terms) == 1:
            if not overlap or score < 0.45:
                continue
        elif len(overlap) < 2 or coverage < 0.50:
            continue

        seen_content.add(normalized_content)

        results.append({
            "title": chunk.document.title,
            "source_url": chunk.document.source_url,
            "chunk_index": chunk.chunk_index,
            "score": score,
            "content": content,
        })

        if len(results) >= requested_k:
            break

    return results


def _guidance_search_terms(text):
    terms = _guidance_terms(text)
    aliases = {
        "laptop": "device",
        "laptops": "device",
        "stolen": "lost",
        "missing": "lost",
        "theft": "lost",
        "securely": "secure",
        "sharing": "share",
        "shares": "share",
        "shared": "share",
        "files": "file",
        "documents": "document",
        "coworkers": "coworker",
        "requesting": "request",
        "requested": "request",
        "requests": "request",
    }
    return {aliases.get(term, term) for term in terms}

def search_guidance_docs(query, top_k=5):
    """Find Guidance-only retrieval; leaves AI Solution search unchanged."""
    if not isinstance(query, str) or not query.strip():
        return []

    index, chunks, model = get_search_index()
    if index is None or not chunks:
        return []

    vector = model.encode(
        [query.strip()],
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    ).astype("float32")

    scores, positions = index.search(vector, min(30, len(chunks)))
    query_terms = _guidance_search_terms(query)
    results, seen = [], set()

    blocked = (
        "acceptance test", "evaluation rubric", "release gate",
        "implementation checklist", "internal governance",
        "prompt injection test", "retrieval test case",
    )

    for score, position in zip(scores[0], positions[0]):
        if position < 0 or float(score) < 0.50:
            continue

        chunk = chunks[int(position)]
        content = (chunk.content or "").strip()
        normalized = " ".join(content.lower().split())

        if not normalized or normalized in seen:
            continue
        if any(term in normalized for term in blocked):
            continue

        overlap = query_terms & _guidance_search_terms(content)
        coverage = len(overlap) / max(1, len(query_terms))

        if len(query_terms) == 1:
            if len(overlap) < 1 or float(score) < 0.45:
                continue
        elif len(overlap) < 2 or coverage < 0.50:
            continue

        seen.add(normalized)
        results.append({
            "title": chunk.document.title,
            "source_url": chunk.document.source_url,
            "chunk_index": chunk.chunk_index,
            "score": float(score),
            "content": content,
            "status": "Draft Guidance",
        })
        if len(results) >= max(1, int(top_k)):
            break

    return results
