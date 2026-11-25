import os
from urllib.parse import urlsplit

from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()


def search_web(query):

    api_key = os.getenv("TAVILY_API_KEY")

    if not api_key:
        raise RuntimeError("Tavily API key is missing")

    client = TavilyClient(api_key=api_key)

    maximum = max(
        1,
        min(
            5,
            int(os.getenv("WEB_SEARCH_MAX_RESULTS", "3"))
        )
    )

    response = client.search(
        query=query,
        search_depth="basic",
        max_results=maximum,
        include_answer=False,
        include_raw_content=False
    )

    sources = []
    context = []
    seen = set()

    for result in response.get("results", []):

        url = result.get("url", "")
        parsed = urlsplit(url)

        if parsed.scheme not in ("http", "https"):
            continue

        if not parsed.netloc or url in seen:
            continue

        seen.add(url)

        title = result.get("title") or url
        content = result.get("content") or ""

        sources.append({
            "title": title,
            "url": url
        })

        context.append(
            f"Source {len(sources)}\n"
            f"Title: {title}\n"
            f"URL: {url}\n"
            f"Content: {content[:1500]}"
        )

    if not sources:
        raise RuntimeError("No web search results found")

    return "\n\n".join(context), sources
