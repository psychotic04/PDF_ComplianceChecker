import os
from functools import lru_cache
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_CACHE_DIR = PROJECT_ROOT / ".model_cache" / "torch"
HF_CACHE_DIR = PROJECT_ROOT / ".model_cache" / "huggingface"
TOXICITY_THRESHOLD = 0.65
ABUSIVE_LABELS = ["toxicity", "severe_toxicity", "obscene", "threat", "insult", "identity_attack"]
FALLBACK_PATTERNS = {
    "threat": ["threaten", "kill", "hurt you", "attack", "destroy you"],
    "insult": ["worthless", "idiot", "stupid", "shut up"],
    "harassment": ["harass", "bully", "humiliate"],
    "illegal_activity": ["illegal", "fraud", "bribe", "blackmail"],
}


@lru_cache(maxsize=1)
def get_detoxify_model():
    MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    HF_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("TORCH_HOME", str(MODEL_CACHE_DIR))
    os.environ.setdefault("HF_HOME", str(HF_CACHE_DIR))
    os.environ.setdefault("TRANSFORMERS_CACHE", str(HF_CACHE_DIR))

    from detoxify import Detoxify

    return Detoxify("original")


def detect_abusive_text(texts: list[str]) -> list[dict[str, Any]]:
    if not texts:
        return []

    try:
        predictions = get_detoxify_model().predict(texts)
    except ModuleNotFoundError:
        return _fallback_detect_abusive_text(texts)
    except Exception:
        return _fallback_detect_abusive_text(texts)

    results = []
    for index, _text in enumerate(texts):
        scores = {
            label: float(predictions.get(label, [0.0] * len(texts))[index])
            for label in ABUSIVE_LABELS
        }
        flagged = {label: score for label, score in scores.items() if score >= TOXICITY_THRESHOLD}
        if flagged:
            reason = ", ".join(f"{label}={score:.2f}" for label, score in sorted(flagged.items()))
        else:
            top_label, top_score = max(scores.items(), key=lambda item: item[1])
            reason = f"No abusive content above threshold. Highest score: {top_label}={top_score:.2f}"

        results.append(
            {
                "abusive": bool(flagged),
                "reason": reason,
                "scores": scores,
            }
        )
    return results


def _fallback_detect_abusive_text(texts: list[str]) -> list[dict[str, Any]]:
    results = []
    for text in texts:
        lowered = text.lower()
        matched_labels = []
        for label, terms in FALLBACK_PATTERNS.items():
            if any(term in lowered for term in terms):
                matched_labels.append(label)

        if matched_labels:
            reason = "Fallback abusive check matched: " + ", ".join(sorted(matched_labels))
        else:
            reason = "No abusive content found by fallback check."

        results.append(
            {
                "abusive": bool(matched_labels),
                "reason": reason,
                "scores": {},
            }
        )
    return results
