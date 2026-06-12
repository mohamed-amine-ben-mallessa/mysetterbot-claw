"""
llm.py — free text generation via OpenRouter, with a model cascade.

The LLM's ONLY job is to write text: openers, follow-ups, replies, and a small
JSON for lead qualification. It never decides to send anything — the agent + the
human do that. Mirrors the hyperframes-free-agent pattern: model writes, code acts.

Needs OPENROUTER_API_KEY in the environment. Zero hard deps (urllib stdlib).
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Optional

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Free models, tried in order. Override with MSBC_MODELS (comma-separated).
DEFAULT_CASCADE = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "google/gemma-4-31b-it:free",
    "openai/gpt-oss-120b:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
]


class LLMError(Exception):
    pass


def _models() -> list[str]:
    env = os.environ.get("MSBC_MODELS", "").strip()
    if env:
        return [m.strip() for m in env.split(",") if m.strip()]
    return DEFAULT_CASCADE


def _api_key() -> str:
    k = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not k:
        raise LLMError("Set OPENROUTER_API_KEY to use text generation.")
    return k


def _extract_text(payload: dict) -> Optional[str]:
    """Pull the assistant text out of an OpenRouter response (handles variants)."""
    try:
        msg = payload["choices"][0]["message"]
    except (KeyError, IndexError, TypeError):
        return None
    content = msg.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()
    if isinstance(content, list):  # some models return content as parts
        parts = [p.get("text", "") for p in content if isinstance(p, dict)]
        joined = "".join(parts).strip()
        if joined:
            return joined
    # reasoning-only fallback
    r = msg.get("reasoning")
    if isinstance(r, str) and r.strip():
        return r.strip()
    return None


def complete(system: str, user: str, *, temperature: float = 0.7,
             max_tokens: int = 600, timeout: int = 60) -> str:
    """Run the free-model cascade until one returns text. Raises LLMError if all fail."""
    key = _api_key()
    last_err = ""
    for model in _models():
        body = json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }).encode("utf-8")
        req = urllib.request.Request(
            OPENROUTER_URL, data=body, method="POST",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "X-Title": "mysetterbot-claw",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                payload = json.load(r)
            text = _extract_text(payload)
            if text:
                return text
            last_err = f"{model}: empty content"
        except urllib.error.HTTPError as e:
            last_err = f"{model}: HTTP {e.code} {e.read().decode('utf-8','replace')[:120]}"
            continue  # rate-limited / unavailable -> next model
        except Exception as e:  # noqa: BLE001
            last_err = f"{model}: {e}"
            continue
    raise LLMError(f"All free models failed. Last: {last_err}")


def complete_json(system: str, user: str, **kw) -> dict:
    """Like complete(), but strips code fences and parses JSON."""
    raw = complete(system, user, **kw)
    s = raw.strip()
    if s.startswith("```"):
        s = s.split("```", 2)[1] if s.count("```") >= 2 else s.strip("`")
        if s.lstrip().lower().startswith("json"):
            s = s.lstrip()[4:]
    s = s.strip()
    # grab the first {...} block if there is leading prose
    if not s.startswith("{"):
        i, j = s.find("{"), s.rfind("}")
        if i != -1 and j != -1:
            s = s[i:j + 1]
    return json.loads(s)
