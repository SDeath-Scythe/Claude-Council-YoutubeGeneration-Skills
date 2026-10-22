"""A small phrase matcher over normalised token keys.

Phrases are compared key-by-key (see ``normalize.token_key``). The first token
of a phrase may carry attached proclitics in the text (ببغداد, والكرادة), the
following tokens must match exactly. Tokens whose key is empty (stand-alone
``:``, ``al``, punctuation) are skipped transparently.

A phrase written with a leading ``!`` requires its first word to carry the
definite article in the text. This is used for place names that double as
personal names or ordinary words: ``!المنصور`` matches "المنصور" or
"بالمنصور" but not the name "منصور".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .normalize import norm_token, prefix_variants, strip_article, tokenize


@dataclass(frozen=True)
class Phrase:
    keys: tuple[str, ...]
    needs_article: bool
    payload: Any


@dataclass(frozen=True)
class Match:
    start: int  # index of first token
    end: int  # index one past the last token
    payload: Any


class PhraseMatcher:
    def __init__(self, entries: Iterable[tuple[str, Any]] = ()):
        self._index: dict[str, list[Phrase]] = {}
        for text, payload in entries:
            self.add(text, payload)

    def add(self, text: str, payload: Any) -> None:
        needs_article = text.startswith("!")
        if needs_article:
            text = text[1:]
        keys = tuple(k for k in (strip_article(norm_token(t))[0] for t in tokenize(text)) if k)
        if not keys:
            return
        phrase = Phrase(keys, needs_article, payload)
        bucket = self._index.setdefault(keys[0], [])
        bucket.append(phrase)
        bucket.sort(key=lambda p: -len(p.keys))

    def match_at(self, tokens: list[str], i: int, norms: list[str] | None = None,
                 *, proclitics: bool = True) -> Match | None:
        """Longest phrase starting exactly at token ``i`` (or None)."""
        if norms is None:
            norms = [norm_token(t) for t in tokens]
        if i >= len(tokens) or not norms[i]:
            return None
        variants = prefix_variants(norms[i]) if proclitics else [norms[i]]
        for variant in variants:
            first_key, had_article = strip_article(variant)
            if not first_key:
                continue
            for phrase in self._index.get(first_key, ()):
                if phrase.needs_article and not had_article:
                    continue
                end = self._match_rest(phrase.keys, norms, i + 1)
                if end is not None:
                    return Match(i, end, phrase.payload)
        return None

    def find_all(self, tokens: list[str]) -> list[Match]:
        """Non-overlapping, left-to-right, longest-first matches."""
        norms = [norm_token(t) for t in tokens]
        out: list[Match] = []
        i = 0
        while i < len(tokens):
            m = self.match_at(tokens, i, norms)
            if m:
                out.append(m)
                i = m.end
            else:
                i += 1
        return out

    @staticmethod
    def _match_rest(keys: tuple[str, ...], norms: list[str], j: int) -> int | None:
        for key in keys[1:]:
            while j < len(norms) and not strip_article(norms[j])[0]:
                j += 1
            if j >= len(norms) or strip_article(norms[j])[0] != key:
                return None
            j += 1
        return j


def key_set(words: Iterable[str]) -> frozenset[str]:
    """Normalised single-word keys (article stripped)."""
    return frozenset(k for k in (strip_article(norm_token(w))[0] for w in words) if k)


def token_in(token: str, keys: frozenset[str]) -> bool:
    """Is ``token`` (allowing proclitics like ب/و/ال) one of ``keys``?"""
    for v in prefix_variants(norm_token(token)):
        if strip_article(v)[0] in keys:
            return True
    return False
