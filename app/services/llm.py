import httpx
from app.config import settings

class LLMError(RuntimeError):
    pass

async def generate(prompt: str, system: str = "", language: str = "en") -> str:
    payload = {
        "model": settings.ollama_model,
        "stream": False,
        "messages": [
            {"role": "system", "content": system or "You are Gram Sahayak, a careful agricultural assistant. Never invent live prices or weather."},
            {"role": "user", "content": prompt},
        ],
        "options": {"temperature": 0.3},
    }
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(f"{settings.ollama_base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
            answer = data.get("message", {}).get("content", "").strip()
            if not answer:
                raise LLMError("Ollama returned an empty response.")
            return answer
    except httpx.ConnectError as exc:
        raise LLMError("Cannot connect to Ollama. Start Ollama and verify OLLAMA_BASE_URL.") from exc
    except httpx.HTTPStatusError as exc:
        raise LLMError(f"Ollama returned HTTP {exc.response.status_code}. Check that OLLAMA_MODEL matches `ollama list`.") from exc
    except httpx.TimeoutException as exc:
        raise LLMError("Ollama took too long to respond. Try a shorter question.") from exc
