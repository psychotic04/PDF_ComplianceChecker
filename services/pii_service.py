import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TLDEXTRACT_CACHE_DIR = PROJECT_ROOT / ".model_cache" / "tldextract"

PII_ENTITIES = [
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "CREDIT_CARD",
    "IN_AADHAAR",
    "IN_PAN",
]
ENTITY_PRIORITY = {
    "EMAIL_ADDRESS": 5,
    "CREDIT_CARD": 5,
    "PHONE_NUMBER": 4,
    "IN_PAN": 4,
    "IN_AADHAAR": 3,
}
FALLBACK_PATTERNS = {
    "EMAIL_ADDRESS": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "PHONE_NUMBER": re.compile(r"(?:\+91[-\s]?)?[6-9]\d{9}\b"),
    "IN_AADHAAR": re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"),
    "IN_PAN": re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"),
    "CREDIT_CARD": re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
}


@lru_cache(maxsize=1)
def get_pii_analyzer():
    TLDEXTRACT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("TLDEXTRACT_CACHE", str(TLDEXTRACT_CACHE_DIR))

    import spacy
    import tldextract
    from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
    from presidio_analyzer.nlp_engine import NlpArtifacts, NlpEngine
    from presidio_analyzer.recognizer_registry import RecognizerRegistry

    tldextract.tldextract.TLD_EXTRACTOR = tldextract.TLDExtract(
        cache_dir=str(TLDEXTRACT_CACHE_DIR),
        suffix_list_urls=(),
        fallback_to_snapshot=True,
    )

    class BlankNlpEngine(NlpEngine):
        def __init__(self) -> None:
            self.nlp = spacy.blank("en")
            self.loaded = False

        def load(self) -> None:
            self.loaded = True

        def is_loaded(self) -> bool:
            return self.loaded

        def process_text(self, text: str, language: str) -> NlpArtifacts:
            doc = self.nlp.make_doc(text)
            return NlpArtifacts(
                entities=[],
                tokens=doc,
                tokens_indices=[token.idx for token in doc],
                lemmas=[token.text.lower() for token in doc],
                nlp_engine=self,
                language=language,
            )

        def process_batch(
            self,
            texts: Iterable[str],
            language: str,
            batch_size: int = 1,
            n_process: int = 1,
            **kwargs,
        ):
            for text in texts:
                yield text, self.process_text(text, language)

        def is_stopword(self, word: str, language: str) -> bool:
            return bool(self.nlp.vocab[word].is_stop)

        def is_punct(self, word: str, language: str) -> bool:
            return bool(self.nlp.vocab[word].is_punct)

        def get_supported_entities(self) -> list[str]:
            return []

        def get_supported_languages(self) -> list[str]:
            return ["en"]

    nlp_engine = BlankNlpEngine()
    nlp_engine.load()
    registry = RecognizerRegistry(supported_languages=["en"])
    registry.load_predefined_recognizers(languages=["en"], nlp_engine=nlp_engine)
    registry.add_recognizer(
        PatternRecognizer(
            supported_entity="IN_AADHAAR",
            patterns=[
                Pattern(
                    name="indian_aadhaar",
                    regex=r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
                    score=0.85,
                )
            ],
            supported_language="en",
        )
    )
    registry.add_recognizer(
        PatternRecognizer(
            supported_entity="IN_PAN",
            patterns=[
                Pattern(
                    name="indian_pan",
                    regex=r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
                    score=0.85,
                )
            ],
            supported_language="en",
        )
    )
    return AnalyzerEngine(nlp_engine=nlp_engine, registry=registry, supported_languages=["en"])


def detect_pii(text: str) -> list[str]:
    try:
        analyzer = get_pii_analyzer()
        results = analyzer.analyze(
            text=text,
            language="en",
            entities=PII_ENTITIES,
            score_threshold=0.35,
        )
        matches = []
        for result in _dedupe_overlapping_results(results):
            value = text[result.start : result.end].strip()
            if value:
                matches.append(f"{result.entity_type}: {value}")
        return matches
    except ModuleNotFoundError:
        return _fallback_detect_pii(text)


def _fallback_detect_pii(text: str) -> list[str]:
    matches = []
    for entity_type, pattern in FALLBACK_PATTERNS.items():
        for match in pattern.findall(text):
            value = match.strip()
            if value:
                matches.append(f"{entity_type}: {value}")
    return sorted(set(matches))


def _dedupe_overlapping_results(results):
    sorted_results = sorted(
        results,
        key=lambda result: (
            ENTITY_PRIORITY.get(result.entity_type, 0),
            result.score,
            result.end - result.start,
        ),
        reverse=True,
    )
    accepted = []
    occupied_spans: list[tuple[int, int]] = []
    for result in sorted_results:
        overlaps = any(result.start < end and result.end > start for start, end in occupied_spans)
        if overlaps:
            continue
        accepted.append(result)
        occupied_spans.append((result.start, result.end))
    return sorted(accepted, key=lambda result: (result.start, result.end))
