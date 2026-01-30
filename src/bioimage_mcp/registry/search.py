from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from math import log


def any_tag_matches(function_tags: Iterable[str], required_tags: list[str] | None) -> bool:
    if not required_tags:
        return True
    tag_set = set(function_tags)
    return any(tag in tag_set for tag in required_tags)


def io_type_matches(ports: Iterable[dict], artifact_type: str | None) -> bool:
    if not artifact_type:
        return True
    for p in ports:
        ptype = p.get("artifact_type")
        if isinstance(ptype, list):
            if artifact_type in ptype:
                return True
        elif ptype == artifact_type:
            return True
    return False


class SearchIndex:
    """Search index for typo-tolerant ranked queries."""

    def tokenize(self, text: str, *, ngram_size: int = 3) -> list[str]:
        if not text:
            return []

        normalized_chars: list[str] = []
        for char in text.lower():
            if char.isalnum():
                normalized_chars.append(char)
            else:
                normalized_chars.append(" ")
        normalized = "".join(normalized_chars)

        tokens: list[str] = []
        for word in normalized.split():
            if len(word) < ngram_size:
                tokens.append(word)
                continue
            for idx in range(len(word) - ngram_size + 1):
                tokens.append(word[idx : idx + ngram_size])
        return tokens

    def rank(self, *, keywords: list[str], candidates: list[dict]) -> list[dict]:
        normalized_keywords: list[str] = []
        seen: set[str] = set()
        for keyword in keywords:
            cleaned = str(keyword).strip().lower()
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            normalized_keywords.append(cleaned)

        if not normalized_keywords:
            raise ValueError("keywords must not be empty")

        if not candidates:
            return []

        fields = (
            ("name", 3.0),
            ("description", 2.0),
            ("tags", 1.0),
        )
        k1 = 1.2
        min_match_ratio = 0.3

        keyword_ngrams = {kw: self.tokenize(kw) for kw in normalized_keywords}

        prepared: list[dict] = []
        for candidate in candidates:
            candidate_id = candidate.get("id") or candidate.get("fn_id")
            if not candidate_id:
                continue
            normalized_candidate = dict(candidate)
            normalized_candidate["id"] = candidate_id
            normalized_candidate.pop("fn_id", None)

            name_text = f"{normalized_candidate.get('name', '')} {normalized_candidate.get('id', '')}".strip()
            description_text = str(normalized_candidate.get("description") or "")
            tags_text = " ".join(normalized_candidate.get("tags") or [])

            name_tokens = self.tokenize(name_text)
            description_tokens = self.tokenize(description_text)
            tags_tokens = self.tokenize(tags_text)

            prepared.append(
                {
                    **normalized_candidate,
                    "_counts": {
                        "name": Counter(name_tokens),
                        "description": Counter(description_tokens),
                        "tags": Counter(tags_tokens),
                    },
                    "_sets": {
                        "name": set(name_tokens),
                        "description": set(description_tokens),
                        "tags": set(tags_tokens),
                    },
                }
            )

        doc_count = len(prepared)
        doc_frequency: dict[str, int] = {kw: 0 for kw in normalized_keywords}
        for keyword, ngrams in keyword_ngrams.items():
            if not ngrams:
                continue
            ngram_set = set(ngrams)
            for entry in prepared:
                if any(ngram_set & entry["_sets"][field] for field, _weight in fields):
                    doc_frequency[keyword] += 1

        idf_scores: dict[str, float] = {}
        for keyword, df in doc_frequency.items():
            if df <= 0:
                idf_scores[keyword] = 0.0
                continue
            idf_scores[keyword] = log(1 + (doc_count - df + 0.5) / (df + 0.5))

        ranked: list[dict] = []
        for entry in prepared:
            score = 0.0
            match_count = 0
            for keyword, ngrams in keyword_ngrams.items():
                if not ngrams:
                    continue
                matched = False
                idf = idf_scores.get(keyword, 0.0)
                for field, weight in fields:
                    counts = entry["_counts"][field]
                    tf = sum(counts.get(ngram, 0) for ngram in ngrams)
                    if tf <= 0:
                        continue
                    overlap_ratio = tf / len(ngrams)
                    if overlap_ratio < min_match_ratio:
                        continue
                    matched = True
                    field_score = (tf * (k1 + 1)) / (tf + k1)
                    score += weight * idf * overlap_ratio * field_score
                if matched:
                    match_count += 1

            if match_count == 0:
                continue

            ranked.append(
                {
                    **{k: v for k, v in entry.items() if not k.startswith("_")},
                    "score": score,
                    "match_count": match_count,
                }
            )

        ranked.sort(key=lambda item: (-item["match_count"], -item["score"], item["id"]))
        return ranked
