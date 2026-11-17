"""Voice input (Speech-to-Text) and output (Text-to-Speech) for Gram Sahayak."""
from __future__ import annotations

import uuid
from pathlib import Path
from . import config
from .llm import transcribe_audio_gemini

_WHISPER = None


def transcribe(audio_file, preferred_language="en") -> str:
    """Transcribes audio file to text using Gemini Multimodal Audio, with Whisper fallback."""
    if not audio_file:
        return ""

    path = Path(audio_file)
    if not path.exists():
        return ""

    # Primary: Fast and accurate Gemini cloud transcription
    if config.USE_GEMINI and config.GEMINI_KEY:
        try:
            gemini_result = transcribe_audio_gemini(str(path), language=preferred_language)
            if gemini_result and gemini_result.strip():
                return gemini_result.strip()
        except Exception:
            pass

    # Secondary: Local faster-whisper if installed
    global _WHISPER
    try:
        from faster_whisper import WhisperModel
        if _WHISPER is None:
            _WHISPER = WhisperModel("base", device="cpu", compute_type="int8")
        segments, _ = _WHISPER.transcribe(
            str(path),
            language=preferred_language if preferred_language in ("en", "hi") else None,
            beam_size=3,
            vad_filter=True,
        )
        return " ".join(s.text.strip() for s in segments).strip()
    except Exception:
        pass

    return ""


def text_to_speech(text: str, language: str = "en") -> str | None:
    """Converts response text to spoken audio file using gTTS."""
    if not text or not text.strip():
        return None

    lang = "hi" if language == "hi" else "en"
    clean_text = text.replace("*", "").replace("#", "").replace("[", "").replace("]", "").strip()
    clean_text = clean_text[:1200]  # Reasonable length for speech

    if config.TTS_BACKEND == "mms":
        return _mms(clean_text, lang)

    try:
        from gtts import gTTS
        path = config.AUDIO / f"reply_{uuid.uuid4().hex[:12]}.mp3"
        tts = gTTS(text=clean_text, lang=lang, slow=False)
        tts.save(str(path))
        return str(path)
    except Exception:
        # Try MMS fallback
        try:
            return _mms(clean_text, lang)
        except Exception:
            return None


def _mms(text: str, language: str) -> str | None:
    """Offline MMS TTS fallback."""
    try:
        import torch
        import soundfile as sf
        from transformers import VitsModel, AutoTokenizer

        model_name = "facebook/mms-tts-hin" if language == "hi" else "facebook/mms-tts-eng"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = VitsModel.from_pretrained(model_name)

        inputs = tokenizer(text, return_tensors="pt")
        with torch.no_grad():
            samples = model(**inputs).waveform.squeeze().cpu().numpy()
        path = config.AUDIO / f"reply_{uuid.uuid4().hex[:12]}.wav"
        sf.write(str(path), samples, model.config.sampling_rate)
        return str(path)
    except Exception:
        return None
