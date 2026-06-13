"""Small in-memory BM25 store used as the keyword side of hybrid retrieval."""

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List


def tokenize(text: str) -> List[str]:
    if not text:
        return []
    en_tokens = re.findall(r"[a-zA-Z0-9+#.\-]{2,}", text.lower())
    cn_tokens = re.findall(r"[\u4e00-\u9fff]{1,2}", text)
    return en_tokens + cn_tokens


@dataclass
class KeywordDocument:
    chunk_id: str
    content: str
    metadata: Dict[str, Any]
    term_counts: Counter = field(default_factory=Counter)
    length: int = 0


class BM25Store:
    """Process-local BM25 index. Vector search remains the durable source."""

    def __init__(self):
        self._collections: Dict[str, Dict[str, KeywordDocument]] = defaultdict(dict)
        self._doc_freqs: Dict[str, Counter] = defaultdict(Counter)
        self._avg_len: Dict[str, float] = defaultdict(float)
        self.k1 = 1.5
        self.b = 0.75

    def add(self, collection: str, documents: List[str], ids: List[str], metadatas: List[Dict[str, Any]]):
        for content, chunk_id, metadata in zip(documents, ids, metadatas):
            tokens = tokenize(content)
            term_counts = Counter(tokens)
            old = self._collections[collection].get(chunk_id)
            if old:
                for term in old.term_counts:
                    self._doc_freqs[collection][term] -= 1
            self._collections[collection][chunk_id] = KeywordDocument(
                chunk_id=chunk_id,
                content=content,
                metadata=metadata,
                term_counts=term_counts,
                length=len(tokens),
            )
            for term in term_counts:
                self._doc_freqs[collection][term] += 1
        self._recalculate_avg_len(collection)

    def search(self, collection: str, query: str, top_k: int = 5, filters: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        query_terms = tokenize(query)
        docs = list(self._collections.get(collection, {}).values())
        if filters:
            docs = [doc for doc in docs if all(doc.metadata.get(k) == v for k, v in filters.items())]
        scores = []
        for doc in docs:
            score = self._score(collection, doc, query_terms)
            if score > 0:
                scores.append({
                    "id": doc.chunk_id,
                    "document": doc.content,
                    "metadata": doc.metadata,
                    "keywordScore": score,
                })
        scores.sort(key=lambda item: item["keywordScore"], reverse=True)
        return scores[:top_k]

    def _score(self, collection: str, doc: KeywordDocument, query_terms: List[str]) -> float:
        if not query_terms or doc.length == 0:
            return 0.0
        doc_count = max(len(self._collections.get(collection, {})), 1)
        avg_len = self._avg_len.get(collection) or 1.0
        score = 0.0
        for term in query_terms:
            tf = doc.term_counts.get(term, 0)
            if tf == 0:
                continue
            df = max(self._doc_freqs[collection].get(term, 0), 1)
            idf = math.log(1 + (doc_count - df + 0.5) / (df + 0.5))
            denom = tf + self.k1 * (1 - self.b + self.b * doc.length / avg_len)
            score += idf * (tf * (self.k1 + 1)) / denom
        return score

    def _recalculate_avg_len(self, collection: str):
        docs = self._collections.get(collection, {})
        if not docs:
            self._avg_len[collection] = 0.0
            return
        self._avg_len[collection] = sum(doc.length for doc in docs.values()) / len(docs)


bm25_store = BM25Store()
