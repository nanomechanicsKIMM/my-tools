#!/usr/bin/env python3
"""
Shared relevance scoring with include/exclude term weights.
- Base score: TF-IDF cosine similarity between text and RFP.
- Include terms: add +include_weight for each term present in text.
- Exclude terms: add -exclude_weight for each term present in text.

Used by score_title_relevance.py and score_abstract_relevance.py.
"""
from __future__ import annotations

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def _normalize_terms(terms: list[str]) -> list[str]:
    return [t.strip() for t in terms if t and t.strip()]


def _count_terms_in_text(text: str, terms: list[str], case_insensitive: bool = True) -> int:
    if not text or not terms:
        return 0
    t = text.upper() if case_insensitive else text
    count = 0
    for term in terms:
        if not term:
            continue
        needle = term.upper() if case_insensitive else term
        if needle in t:
            count += 1
    return count


def score_texts_relevance_weighted(
    texts: list[str],
    rfp_text: str,
    include_terms: list[str] | None = None,
    exclude_terms: list[str] | None = None,
    include_weight: float = 0.2,
    exclude_weight: float = 0.5,
) -> list[float]:
    """
    Score each text by: base (TF-IDF cosine vs RFP) + include_bonus - exclude_penalty.
    Returns list of scores in same order as texts.
    """
    include_terms = _normalize_terms(include_terms or [])
    exclude_terms = _normalize_terms(exclude_terms or [])

    corpus = [rfp_text] + [t or " " for t in texts]
    vectorizer = TfidfVectorizer(
        max_features=8000,
        stop_words="english",
        ngram_range=(1, 2),
        min_df=1,
        max_df=0.95,
    )
    X = vectorizer.fit_transform(corpus)
    rfp_vec = X[0:1]
    base_scores = cosine_similarity(X[1:], rfp_vec).ravel()

    result = []
    for i, text in enumerate(texts):
        base = float(base_scores[i]) if i < len(base_scores) else 0.0
        inc = _count_terms_in_text(text or "", include_terms) * include_weight
        exc = _count_terms_in_text(text or "", exclude_terms) * exclude_weight
        score = base + inc - exc
        result.append(round(score, 4))
    return result


def score_abstract_claim_pairs_relevance_weighted(
    abstracts: list[str],
    claims: list[str],
    rfp_text: str,
    include_terms: list[str] | None = None,
    exclude_terms: list[str] | None = None,
    include_weight: float = 0.2,
    exclude_weight: float = 0.5,
    abstract_weight: float = 0.5,
    claim_weight: float = 0.5,
) -> list[float]:
    """
    Score each row by: 0.5 * (abstract–RFP cosine) + 0.5 * (claim–RFP cosine) + include_bonus - exclude_penalty.
    Include/exclude counts are applied to combined text (abstract + claim).
    If claim is empty, that row uses abstract_weight for abstract and 0 for claim (so 100% abstract when claim_weight 0.5).
    Returns list of scores in same order as inputs.
    """
    include_terms = _normalize_terms(include_terms or [])
    exclude_terms = _normalize_terms(exclude_terms or [])
    n = max(len(abstracts), len(claims))
    abstracts = list(abstracts) + [""] * (n - len(abstracts))
    claims = list(claims) + [""] * (n - len(claims))

    # Base: abstract vs RFP
    corpus_abs = [rfp_text] + [a or " " for a in abstracts]
    vec = TfidfVectorizer(max_features=8000, stop_words="english", ngram_range=(1, 2), min_df=1, max_df=0.95)
    X_abs = vec.fit_transform(corpus_abs)
    scores_abs = cosine_similarity(X_abs[1:], X_abs[0:1]).ravel()

    # Base: claim vs RFP (same RFP, so fit again with claim texts)
    corpus_claim = [rfp_text] + [c or " " for c in claims]
    vec_claim = TfidfVectorizer(max_features=8000, stop_words="english", ngram_range=(1, 2), min_df=1, max_df=0.95)
    X_claim = vec_claim.fit_transform(corpus_claim)
    scores_claim = cosine_similarity(X_claim[1:], X_claim[0:1]).ravel()

    result = []
    for i in range(n):
        s_abs = float(scores_abs[i]) if i < len(scores_abs) else 0.0
        s_claim = float(scores_claim[i]) if i < len(scores_claim) else 0.0
        a, c = abstracts[i] or "", claims[i] or ""
        if not c.strip():
            # No claim: use abstract only (100% abstract)
            base = s_abs
        else:
            base = abstract_weight * s_abs + claim_weight * s_claim
        combined = f"{a} {c}".strip()
        inc = _count_terms_in_text(combined, include_terms) * include_weight
        exc = _count_terms_in_text(combined, exclude_terms) * exclude_weight
        score = base + inc - exc
        result.append(round(score, 4))
    return result
