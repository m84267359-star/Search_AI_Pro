import os
import time
from threading import Lock

from dotenv import load_dotenv

load_dotenv()

ECONOMY_MODEL = os.getenv(
    "GEMINI_ECONOMY_MODEL",
    "gemini-3.1-flash-lite"
)

BACKUP_MODEL = os.getenv(
    "GEMINI_BACKUP_MODEL",
    "gemini-3.5-flash-lite"
)

BALANCED_MODEL = os.getenv(
    "GEMINI_BALANCED_MODEL",
    "gemini-3.5-flash"
)

PERFORMANCE_MODEL = os.getenv(
    "GEMINI_PERFORMANCE_MODEL",
    "gemini-3.6-flash"
)

ADVANCED_MODEL = os.getenv(
    "GEMINI_ADVANCED_MODEL",
    "gemini-3.8-flash"
)

MODEL_LABELS = {
    "auto": "Auto - Token Efficient",
    ECONOMY_MODEL: "Gemini 3.1 Flash-Lite",
    BACKUP_MODEL: "Gemini 3.5 Flash-Lite",
    BALANCED_MODEL: "Gemini 3.5 Flash",
    PERFORMANCE_MODEL: "Gemini 3.6 Flash",
    ADVANCED_MODEL: "Gemini 3.8 Flash"
}

MODELS = set(MODEL_LABELS)

cooldowns = {}
cooldown_lock = Lock()


def enabled(name, default="true"):
    return os.getenv(name, default).lower() == "true"


def mark_unavailable(model):
    seconds = int(
        os.getenv("MODEL_COOLDOWN_SECONDS", "300")
    )

    with cooldown_lock:
        cooldowns[model] = time.monotonic() + seconds


def is_available(model):
    with cooldown_lock:
        return time.monotonic() >= cooldowns.get(model, 0)


def get_model_candidates(selected="auto"):

    if selected not in MODELS:
        raise ValueError("Invalid model selected")

    # Manual selection must never silently change.
    if selected != "auto":
        return [selected]

    # Always try lightweight models first.
    candidates = [
        ECONOMY_MODEL,
        BACKUP_MODEL,
        BALANCED_MODEL,
        PERFORMANCE_MODEL
    ]

    if enabled("ALLOW_ADVANCED_IN_AUTO", "false"):
        candidates.append(ADVANCED_MODEL)

    candidates = list(dict.fromkeys(candidates))

    candidates = [
        model for model in candidates
        if is_available(model)
    ]

    if not enabled("MODEL_FALLBACK_ENABLED"):
        return candidates[:1]

    max_attempts = max(
        1,
        int(os.getenv("MAX_MODEL_ATTEMPTS", "2"))
    )

    return candidates[:max_attempts]


def can_fallback(error):
    code = getattr(error, "code", None)

    try:
        code = int(code)
    except (ValueError, TypeError):
        return False

    return code in (404, 429, 500, 502, 503, 504)
