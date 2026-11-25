import os
import re

from dotenv import load_dotenv

load_dotenv()


def classify_task(prompt, web_search=False, document=False):

    text = prompt.lower().strip()

    if web_search or document:
        return "coding"

    if re.fullmatch(
        r"(hi|hello|hey|hlo|hye|thanks|thank you|"
        r"good morning|good evening|how are you)[!?. ]*",
        text
    ):
        return "greeting"

    complex_keywords = [
        "system design",
        "architecture",
        "complete project",
        "production ready",
        "detailed analysis",
        "multi agent",
        "step by step implementation"
    ]

    coding_keywords = [
        "python",
        "javascript",
        "flask",
        "fastapi",
        "sql",
        "code",
        "debug",
        "program",
        "function",
        "error",
        "algorithm"
    ]

    if any(word in text for word in complex_keywords):
        return "complex"

    if any(word in text for word in coding_keywords):
        return "coding"

    if len(text.split()) <= 15:
        return "simple"

    return "medium"


def get_output_limit(
    prompt,
    web_search=False,
    document=False
):

    maximum = int(
        os.getenv("MAX_OUTPUT_TOKENS", "4096")
    )

    if os.getenv(
        "TOKEN_OPTIMIZATION", "true"
    ).lower() != "true":
        return maximum

    task = classify_task(
        prompt,
        web_search,
        document
    )

    limits = {
        "greeting": int(
            os.getenv("GREETING_TASK_TOKENS", "128")
        ),
        "simple": int(
            os.getenv("SIMPLE_TASK_TOKENS", "512")
        ),
        "medium": int(
            os.getenv("MEDIUM_TASK_TOKENS", "1024")
        ),
        "coding": int(
            os.getenv("CODING_TASK_TOKENS", "2048")
        ),
        "complex": int(
            os.getenv("COMPLEX_TASK_TOKENS", "4096")
        )
    }

    return min(limits[task], maximum)


def limit_history(messages):

    maximum = int(
        os.getenv("MAX_HISTORY_MESSAGES", "10")
    )

    if maximum <= 0:
        return []

    return messages[-maximum:]
