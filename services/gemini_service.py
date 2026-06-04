import json
import os
import re
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google import genai


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"


class GeminiService:
    def __init__(self) -> None:
        load_dotenv(ENV_PATH, override=True)
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None

    @property
    def enabled(self) -> bool:
        return self.client is not None

    def analyze_json(self, prompt: str, fallback: dict[str, Any]) -> dict[str, Any]:
        if not self.client:
            return {
                **fallback,
                "reason": "Gemini API key is not configured. Set GEMINI_API_KEY in .env.",
            }

        last_error = ""
        for attempt in range(3):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config={"response_mime_type": "application/json"},
                )
                return self._parse_json(response.text, fallback)
            except Exception as exc:
                last_error = str(exc)
                if not self._is_transient_error(last_error) or attempt == 2:
                    break
                time.sleep(2**attempt)

        return {
            **fallback,
            "reason": self._friendly_error_message(last_error),
        }

    def analyze_json_batch(
        self,
        prompt_name: str,
        texts: list[str],
        result_key: str,
        fallback: dict[str, Any],
    ) -> list[dict[str, Any]]:
        results, _usage = self.analyze_json_batch_with_usage(prompt_name, texts, result_key, fallback)
        return results

    def analyze_json_batch_with_usage(
        self,
        prompt_name: str,
        texts: list[str],
        result_key: str,
        fallback: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        if not texts:
            return [], empty_usage()

        if not self.client:
            return [
                {
                    **fallback,
                    "reason": "Gemini API key is not configured. Set GEMINI_API_KEY in .env.",
                }
                for _ in texts
            ], empty_usage()

        prompt = build_batch_prompt(prompt_name, texts, result_key)
        last_error = ""
        for attempt in range(3):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config={"response_mime_type": "application/json"},
                )
                return self._parse_json_list(response.text, fallback, len(texts)), extract_usage(response)
            except Exception as exc:
                last_error = str(exc)
                if not self._is_transient_error(last_error) or attempt == 2:
                    break
                time.sleep(2**attempt)

        return [
            {
                **fallback,
                "reason": self._friendly_error_message(last_error),
            }
            for _ in texts
        ], empty_usage()

    @staticmethod
    def _is_transient_error(error_text: str) -> bool:
        transient_markers = [
            "503",
            "UNAVAILABLE",
            "high demand",
            "429",
            "RESOURCE_EXHAUSTED",
            "rate limit",
            "timeout",
        ]
        return any(marker.lower() in error_text.lower() for marker in transient_markers)

    @staticmethod
    def _friendly_error_message(error_text: str) -> str:
        if GeminiService._is_transient_error(error_text):
            return (
                "AI analysis is temporarily unavailable because the Gemini model is under high demand. "
                "Please retry the scan in a few minutes."
            )
        return "AI analysis could not be completed. Please verify the Gemini API key and model configuration."

    @staticmethod
    def _parse_json(raw_text: str | None, fallback: dict[str, Any]) -> dict[str, Any]:
        if not raw_text:
            return fallback

        cleaned = raw_text.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            parsed = json.loads(cleaned)
            return parsed if isinstance(parsed, dict) else fallback
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
            if not match:
                return fallback
            try:
                parsed = json.loads(match.group(0))
                return parsed if isinstance(parsed, dict) else fallback
            except json.JSONDecodeError:
                return fallback

    @staticmethod
    def _parse_json_list(raw_text: str | None, fallback: dict[str, Any], expected_count: int) -> list[dict[str, Any]]:
        if not raw_text:
            return [fallback.copy() for _ in range(expected_count)]

        cleaned = raw_text.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)

        parsed: Any
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\[.*\]", cleaned, flags=re.DOTALL)
            if not match:
                return [fallback.copy() for _ in range(expected_count)]
            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError:
                return [fallback.copy() for _ in range(expected_count)]

        if not isinstance(parsed, list):
            return [fallback.copy() for _ in range(expected_count)]

        results = []
        for item in parsed[:expected_count]:
            results.append(item if isinstance(item, dict) else fallback.copy())

        while len(results) < expected_count:
            results.append(fallback.copy())
        return results


def load_prompt(name: str, text: str) -> str:
    prompt_path = Path("prompts") / name
    return prompt_path.read_text(encoding="utf-8").replace("{text}", text)


def build_batch_prompt(name: str, texts: list[str], result_key: str) -> str:
    prompt_path = Path("prompts") / name
    base_prompt = prompt_path.read_text(encoding="utf-8")
    chunks = "\n\n".join(
        f"Chunk {index}:\n{text}"
        for index, text in enumerate(texts, start=1)
    )
    batch_instruction = (
        f"Analyze each chunk independently. Return only JSON as an array with exactly {len(texts)} "
        f"objects in the same order as the chunks. Each object must contain \"{result_key}\" as a "
        "boolean and \"reason\" as a string."
    )
    batch_prompt = re.sub(
        r"Return (?:only )?JSON(?: only)?\.",
        batch_instruction,
        base_prompt,
        flags=re.IGNORECASE,
    )
    batch_prompt = re.sub(
        r"\{\s*\"" + re.escape(result_key) + r"\".*?\}",
        "",
        batch_prompt,
        flags=re.DOTALL,
    )
    return batch_prompt.replace("{text}", chunks)


def empty_usage() -> dict[str, int]:
    return {
        "prompt_tokens": 0,
        "candidate_tokens": 0,
        "total_tokens": 0,
    }


def extract_usage(response: Any) -> dict[str, int]:
    usage = getattr(response, "usage_metadata", None)
    if usage is None:
        return empty_usage()

    return {
        "prompt_tokens": _usage_int(usage, "prompt_token_count"),
        "candidate_tokens": _usage_int(usage, "candidates_token_count"),
        "total_tokens": _usage_int(usage, "total_token_count"),
    }


def _usage_int(usage: Any, name: str) -> int:
    value = getattr(usage, name, 0)
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
