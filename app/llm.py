"""Unified LLM Provider for Gram Sahayak.

Supports:
- Google Gemini (gemini-3.5-flash-lite, gemini-3.5-flash, gemini-flash-latest) for text, vision, and audio transcription.
- Local Ollama (llama3.2:latest, llama3.2:3b) for offline and local execution.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import time
from typing import Optional

import requests
from . import config

try:
    from google import genai
    from google.genai import types as genai_types
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False


class ModelUnavailable(RuntimeError):
    pass


def _get_gemini_client():
    if not config.USE_GEMINI or not config.GEMINI_KEY:
        return None
    if _GENAI_AVAILABLE:
        try:
            return genai.Client(api_key=config.GEMINI_KEY)
        except Exception:
            return None
    return None


def _candidate_gemini_models() -> list[str]:
    preferred = config.GEMINI_MODEL or "gemini-3.5-flash-lite"
    fallbacks = [
        preferred,
        "gemini-3.5-flash-lite",
        "gemini-3.5-flash",
        "gemini-flash-latest",
        "gemini-flash-lite-latest",
    ]
    # Remove duplicates while preserving order
    seen = set()
    return [m for m in fallbacks if not (m in seen or seen.add(m))]


def gemini_generate(prompt: str, system_instruction: str = "") -> str:
    """Generate text completion using Google Gemini API."""
    if not config.USE_GEMINI or not config.GEMINI_KEY:
        raise ModelUnavailable("Gemini disabled or GEMINI_API_KEY missing in .env")

    client = _get_gemini_client()
    models = _candidate_gemini_models()

    if client:
        for model in models:
            for attempt in range(2):
                try:
                    config_args = {}
                    if system_instruction:
                        config_args["system_instruction"] = system_instruction
                    resp = client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=config_args if config_args else None
                    )
                    if resp and resp.text:
                        return resp.text.strip()
                except Exception as exc:
                    err_str = str(exc)
                    if "503" in err_str or "UNAVAILABLE" in err_str:
                        if attempt == 0:
                            time.sleep(1.0)
                            continue
                        break
                    if "404" in err_str:
                        break  # Model not found/deprecated, try next model
                    if "429" in err_str:
                        raise ModelUnavailable("Gemini rate limit / quota exceeded. Check Google AI Studio.") from exc
                    if "401" in err_str or "403" in err_str:
                        raise ModelUnavailable(f"Gemini API authorization error: {exc}") from exc

    # REST API fallback if google-genai client failed or not available
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1024},
    }
    if system_instruction:
        payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={config.GEMINI_KEY}"
        for attempt in range(2):
            try:
                r = requests.post(url, headers=headers, json=payload, timeout=40)
            except requests.RequestException:
                break
            if r.status_code == 200:
                try:
                    data = r.json()
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        text = "".join(p.get("text", "") for p in parts).strip()
                        if text:
                            return text
                except Exception:
                    pass
            elif r.status_code == 503 and attempt == 0:
                time.sleep(1.0)
                continue
            elif r.status_code == 429:
                raise ModelUnavailable("Gemini rate limit exceeded.")
            elif r.status_code in (401, 403):
                raise ModelUnavailable("Gemini API key invalid or unauthorized.")
            elif r.status_code == 404:
                break

    raise ModelUnavailable("Gemini request could not be completed.")


def local_chat(prompt: str, images: list[str] | None = None, model: str | None = None) -> str:
    """Call local Ollama instance for offline generation."""
    entry = {"role": "user", "content": prompt}
    if images:
        entry["images"] = [base64.b64encode(Path(p).read_bytes()).decode("ascii") for p in images]
    target_model = model or (config.VISION_MODEL if images else config.OLLAMA_MODEL)
    try:
        response = requests.post(
            f"{config.OLLAMA_URL}/api/chat",
            json={
                "model": target_model,
                "messages": [entry],
                "stream": False,
                "options": {"temperature": 0.2, "num_predict": 450},
            },
            timeout=90,
        )
        response.raise_for_status()
        content = response.json()["message"]["content"].strip()
        if not content:
            raise ValueError("empty Ollama completion")
        return content
    except Exception as exc:
        raise ModelUnavailable(f"Local Ollama unavailable: {exc}") from exc


def generate(prompt: str, allow_cloud: bool = True, system_instruction: str = "") -> str:
    """Unified text generation: prefers Gemini when configured, with Ollama fallback."""
    if allow_cloud and config.USE_GEMINI and config.GEMINI_KEY:
        try:
            return gemini_generate(prompt, system_instruction)
        except ModelUnavailable:
            pass  # Fall back to local Ollama

    try:
        return local_chat(prompt)
    except ModelUnavailable:
        if allow_cloud and config.USE_GEMINI and config.GEMINI_KEY:
            return gemini_generate(prompt, system_instruction)
        raise ModelUnavailable(
            "Neither Gemini API nor local Ollama is available. "
            "Please check GEMINI_API_KEY in .env or start Ollama."
        )


def inspect_image(image_path: str, prompt: str) -> str:
    """Inspect plant/crop image using Gemini Multimodal Vision."""
    path = Path(image_path)
    if not path.exists():
        raise ModelUnavailable(f"Image not found: {image_path}")

    mime_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }
    suffix = path.suffix.lower()
    mime = mime_types.get(suffix, "image/jpeg")

    client = _get_gemini_client()
    img_bytes = path.read_bytes()

    if client and _GENAI_AVAILABLE:
        models = _candidate_gemini_models()
        for model in models:
            try:
                part = genai_types.Part.from_bytes(data=img_bytes, mime_type=mime)
                resp = client.models.generate_content(
                    model=model,
                    contents=[prompt, part]
                )
                if resp and resp.text:
                    return resp.text.strip()
            except Exception as exc:
                if "429" in str(exc):
                    raise ModelUnavailable("Gemini quota limit reached.") from exc
                continue

    # REST fallback
    b64_data = base64.b64encode(img_bytes).decode("ascii")
    payload = {
        "contents": [{
            "role": "user",
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": mime, "data": b64_data}}
            ]
        }],
        "generationConfig": {"temperature": 0.15, "maxOutputTokens": 600}
    }
    models = _candidate_gemini_models()
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={config.GEMINI_KEY}"
        try:
            r = requests.post(url, json=payload, timeout=40)
            if r.status_code == 200:
                data = r.json()
                text = "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"]).strip()
                if text:
                    return text
        except Exception:
            continue

    # Last resort: try local Ollama vision if available
    try:
        return local_chat(prompt, images=[image_path], model=config.VISION_MODEL)
    except Exception as exc:
        raise ModelUnavailable(f"Crop vision analysis failed on Gemini and Ollama: {exc}") from exc


def transcribe_audio_gemini(audio_path: str, language: str = "en") -> str:
    """Transcribe audio file using Gemini multimodal audio capabilities."""
    path = Path(audio_path)
    if not path.exists():
        return ""

    mime_types = {
        ".wav": "audio/wav",
        ".mp3": "audio/mp3",
        ".m4a": "audio/m4a",
        ".ogg": "audio/ogg",
        ".webm": "audio/webm",
        ".flac": "audio/flac",
    }
    mime = mime_types.get(path.suffix.lower(), "audio/wav")
    audio_bytes = path.read_bytes()

    lang_instr = "in Hindi" if language == "hi" else "in English"
    prompt = (
        f"Transcribe accurately the spoken words in this audio recording {lang_instr}. "
        "Return ONLY the exact spoken transcription. If the audio is silent or unintelligible, reply ONLY with SILENCE."
    )

    client = _get_gemini_client()
    if client and _GENAI_AVAILABLE:
        for model in _candidate_gemini_models():
            try:
                part = genai_types.Part.from_bytes(data=audio_bytes, mime_type=mime)
                resp = client.models.generate_content(
                    model=model,
                    contents=[prompt, part]
                )
                if resp and resp.text:
                    res = resp.text.strip()
                    if res.upper() == "SILENCE" or not res:
                        return ""
                    return res
            except Exception:
                continue

    # REST fallback
    b64_audio = base64.b64encode(audio_bytes).decode("ascii")
    payload = {
        "contents": [{
            "role": "user",
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": mime, "data": b64_audio}}
            ]
        }]
    }
    for model in _candidate_gemini_models():
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={config.GEMINI_KEY}"
        try:
            r = requests.post(url, json=payload, timeout=30)
            if r.status_code == 200:
                data = r.json()
                text = "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"]).strip()
                if text.upper() == "SILENCE" or not text:
                    return ""
                return text
        except Exception:
            continue
    return ""


def parse_json_object(text: str) -> dict:
    try:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start : end + 1])
    except (json.JSONDecodeError, ValueError):
        pass
    return {}
