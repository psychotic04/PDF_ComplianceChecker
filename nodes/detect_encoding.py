import string
import unicodedata

from langdetect import LangDetectException, detect_langs

from graph.state import ComplianceState


ALLOWED_EXTRA = set("\n\r\t .,;:!?()[]{}'\"-/\\@#$%&*+=_<>|`~")
LANGUAGE_NAMES = {
    "af": "Afrikaans",
    "ca": "Catalan",
    "de": "German",
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "it": "Italian",
    "nl": "Dutch",
    "pt": "Portuguese",
}


def detect_encoding_node(state: ComplianceState) -> ComplianceState:
    results = []
    for page in state.get("pages", []):
        text = page["text"]
        valid = True
        reasons = []

        try:
            text.encode("utf-8").decode("utf-8")
        except UnicodeError:
            valid = False
            reasons.append("Text is not UTF-8 compliant.")

        unsupported = sorted({char for char in text if char not in string.printable and char not in ALLOWED_EXTRA})
        if unsupported:
            valid = False
            reasons.append(_unsupported_character_reason(unsupported))

        if text.strip():
            try:
                languages = detect_langs(text)
                top_language = languages[0] if languages else None
                if top_language and top_language.lang != "en":
                    valid = False
                    reasons.append(_language_reason(top_language))

                snippets = _non_english_snippets(text)
                if snippets:
                    valid = False
                    reasons.append("Non-English text samples: " + " | ".join(snippets))
            except LangDetectException:
                valid = False
                reasons.append("Unable to verify English language content.")

        results.append(
            {
                "page": page["page"],
                "violation": not valid,
                "type": "Encoding",
                "encoding_valid": valid,
                "reason": " ".join(reasons),
            }
        )
    return {**state, "encoding_results": results}


def _unsupported_character_reason(unsupported: list[str]) -> str:
    samples = []
    for char in unsupported[:10]:
        name = unicodedata.name(char, "UNKNOWN")
        samples.append(f"{char} (U+{ord(char):04X}, {name})")
    suffix = "" if len(unsupported) <= 10 else f" and {len(unsupported) - 10} more"
    return f"Unsupported non-ASCII symbols detected: {', '.join(samples)}{suffix}."


def _language_reason(language) -> str:
    language_name = LANGUAGE_NAMES.get(language.lang, language.lang)
    return (
        f"Detected non-English page language: {language.lang} ({language_name}) "
        f"with confidence {language.prob:.2f}. Only English (en) is supported."
    )


def _non_english_snippets(text: str) -> list[str]:
    snippets = []
    seen = set()
    seen_languages = set()
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for index, line in enumerate(lines):
        next_line = lines[index + 1] if index + 1 < len(lines) else ""
        should_join_next = (
            "section:" in line.lower()
            and next_line
            and "section:" not in next_line.lower()
            and "paragraph:" not in next_line.lower()
        )
        candidate = f"{line} {next_line}".strip() if should_join_next else line
        if len(candidate) < 30:
            continue

        try:
            languages = detect_langs(candidate)
        except LangDetectException:
            continue

        if not languages:
            continue

        top_language = languages[0]
        if top_language.lang == "en" or top_language.prob < 0.75:
            continue
        if top_language.lang in seen_languages:
            continue

        language_name = LANGUAGE_NAMES.get(top_language.lang, top_language.lang)
        snippet = f"{top_language.lang} ({language_name}, {top_language.prob:.2f}): {_clean_snippet(candidate)}"
        if snippet not in seen:
            snippets.append(snippet)
            seen.add(snippet)
            seen_languages.add(top_language.lang)
        if len(snippets) == 3:
            break
    return snippets


def _clean_snippet(text: str, limit: int = 140) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 3].rstrip() + "..."
