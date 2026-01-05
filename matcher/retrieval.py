# retrieval.py
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence, Tuple


def _default_text_builder(item: Dict) -> str:
    parts: List[str] = []
    if item.get("event"):
        parts.append(str(item["event"]))
    if item.get("description"):
        parts.append(str(item["description"]))
    return " ".join(parts).strip()


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


@dataclass
class RetrievalResult:
    distances: List[List[float]]
    indices: List[List[int]]


class Retriever:
    def __init__(
        self,
        text_builder: Callable[[Dict], str] | None = None,
        top_k: int = 5,
    ) -> None:
        self.text_builder = text_builder or _default_text_builder
        self.top_k = top_k

        self._embedder = None
        self._faiss = None
        self._faiss_index = None
        self._dimension = None
        self._use_embeddings = False

        try:
            import faiss
            from sentence_transformers import SentenceTransformer
            
            model_candidates = [
                "all-mpnet-base-v2",
                "all-MiniLM-L6-v2",
            ]
            last_err: Optional[Exception] = None
            for name in model_candidates:
                try:
                    self._embedder = SentenceTransformer(name)
                    break
                except Exception as e:
                    last_err = e
                    self._embedder = None
            if self._embedder is None and last_err:
                raise last_err

            self._faiss = faiss
            self._use_embeddings = True
        except Exception:
            self._use_embeddings = False

        self._inv_index: Dict[str, List[int]] = {}
        self._tok_docs: List[Dict[str, int]] = []
        self._doc_norms: List[float] = []

    def _build_embedding_index(self, corpus_texts: Sequence[str]) -> None:
        assert self._embedder is not None and self._faiss is not None
        vecs = self._embedder.encode(list(corpus_texts))  # (N, d)
        self._dimension = vecs.shape[1]
        self._faiss.normalize_L2(vecs)
        self._faiss_index = self._faiss.IndexFlatIP(self._dimension)
        self._faiss_index.add(vecs)
        self._corpus_vecs = vecs

    def _build_token_index(self, corpus_texts: Sequence[str]) -> None:
        inv: Dict[str, List[int]] = {}
        tok_docs: List[Dict[str, int]] = []
        norms: List[float] = []
        for i, text in enumerate(corpus_texts):
            toks = _tokenize(text)
            counts: Dict[str, int] = {}
            for t in toks:
                counts[t] = counts.get(t, 0) + 1
            tok_docs.append(counts)
            for t in counts:
                inv.setdefault(t, []).append(i)
            norm = math.sqrt(sum(c * c for c in counts.values())) or 1.0
            norms.append(norm)
        self._inv_index = inv
        self._tok_docs = tok_docs
        self._doc_norms = norms

    def index(self, corpus_items: Sequence[Dict]) -> None:
        texts = [self.text_builder(it) for it in corpus_items]
        if self._use_embeddings:
            self._build_embedding_index(texts)
        else:
            self._build_token_index(texts)

    def _search_embeddings(self, query_items: Sequence[Dict], k: int) -> RetrievalResult:
        assert (
            self._embedder is not None and self._faiss is not None and self._faiss_index is not None
        )
        q_texts = [self.text_builder(it) for it in query_items]
        q_vecs = self._embedder.encode(q_texts)
        self._faiss.normalize_L2(q_vecs)
        distances, indices = self._faiss_index.search(q_vecs, k)
        # Convert to lists
        return RetrievalResult(
            distances=[list(row) for row in distances],
            indices=[list(map(int, row)) for row in indices],
        )

    def _search_tokens(self, query_items: Sequence[Dict], k: int) -> RetrievalResult:
        # Candidate generation via inverted index union, then cosine over counts
        results_distances: List[List[float]] = []
        results_indices: List[List[int]] = []

        for qi, item in enumerate(query_items):
            q_text = self.text_builder(item)
            q_toks = _tokenize(q_text)
            q_counts: Dict[str, int] = {}
            for t in q_toks:
                q_counts[t] = q_counts.get(t, 0) + 1
            q_norm = math.sqrt(sum(c * c for c in q_counts.values())) or 1.0

            # Gather candidates from inverted index
            cand_set: set[int] = set()
            for t in q_counts.keys():
                cand_set.update(self._inv_index.get(t, ()))

            scored: List[Tuple[float, int]] = []
            for di in cand_set:
                d_counts = self._tok_docs[di]
                # cosine similarity on raw counts
                dot = 0.0
                for t, qc in q_counts.items():
                    dc = d_counts.get(t, 0)
                    if dc:
                        dot += qc * dc
                sim = dot / (q_norm * (self._doc_norms[di] or 1.0))
                if sim > 0:
                    scored.append((sim, di))

            scored.sort(key=lambda x: x[0], reverse=True)
            top = scored[:k]
            results_distances.append([s for s, _ in top])
            results_indices.append([i for _, i in top])

            while len(results_distances[-1]) < k:
                results_distances[-1].append(0.0)
                results_indices[-1].append(-1)

        return RetrievalResult(distances=results_distances, indices=results_indices)

    def search(self, query_items: Sequence[Dict], k: Optional[int] = None) -> RetrievalResult:
        k = k or self.top_k
        if self._use_embeddings:
            return self._search_embeddings(query_items, k)
        return self._search_tokens(query_items, k)
