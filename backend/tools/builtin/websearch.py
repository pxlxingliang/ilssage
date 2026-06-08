import re
import urllib.request
import urllib.parse
import ssl
from datetime import datetime

from backend.tools.registry import ToolInfo

DESCRIPTION_TEMPLATE = """\
Web search tool for retrieving real-time information from the internet.

- Provides up-to-date information for current events and recent data
- Returns search result information formatted as search result blocks
- Use this tool for accessing information beyond ILsSage's knowledge cutoff
- Searches are performed automatically within a single API call

Usage notes:
  - Domain filtering is supported to include or block specific websites
  - Searches are performed using DuckDuckGo (no API key required)
  - Web search is read-only and does not modify any files
  - Results may be summarized if the content is very large

Today's date is {date}. You MUST use this year when searching for recent information or current events."""

PARAMETERS = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "The search query",
        },
        "numResults": {
            "type": "integer",
            "description": "Number of results to return (max 10, default 5)",
            "default": 5,
        },
    },
    "required": ["query"],
}

MAX_RESULTS = 10
DEFAULT_RESULTS = 5

_DDGRESULT = re.compile(
    r'<a[^>]*rel="nofollow"[^>]*class="result-link"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
    re.DOTALL | re.IGNORECASE,
)
_DDGSNIPPET = re.compile(
    r'<td[^>]*class="result-snippet"[^>]*>(.*?)</td>',
    re.DOTALL | re.IGNORECASE,
)
_STRIP_TAGS = re.compile(r"<[^>]+>")
_HTML_ENTITIES = re.compile(r"&[a-z]+;")


def _html_to_text(html: str) -> str:
    text = _STRIP_TAGS.sub("", html)
    text = _HTML_ENTITIES.sub(" ", text)
    return text.strip()


def _execute(query: str, numResults: int = DEFAULT_RESULTS) -> str:
    num = min(max(1, numResults), MAX_RESULTS)

    ctx = ssl.create_default_context()
    encoded = urllib.parse.quote(query)
    ddg_url = f"https://html.duckduckgo.com/html/?q={encoded}"

    req = urllib.request.Request(
        ddg_url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; ILsSage/1.0)",
        },
    )

    try:
        resp = urllib.request.urlopen(req, timeout=15, context=ctx)
        html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return f"Search error: {e}"

    links = _DDGRESULT.findall(html)
    snippets = _DDGSNIPPET.findall(html)

    if not links:
        return "No search results found. Please try a different query."

    results = []
    for i, (url, title) in enumerate(links[:num]):
        title = _html_to_text(title)
        url = urllib.parse.unquote(url)
        snippet = _html_to_text(snippets[i]) if i < len(snippets) else ""
        results.append(f"## {i + 1}. {title}\nURL: {url}\n{snippet}\n")

    today = datetime.now().strftime("%Y-%m-%d")
    header = f"Search results for: {query} (date: {today})\n"
    return header + "\n".join(results)


def create_websearch_tool() -> ToolInfo:
    desc = DESCRIPTION_TEMPLATE.format(date=datetime.now().strftime("%Y-%m-%d"))
    return ToolInfo(
        name="websearch",
        description=desc,
        parameters=PARAMETERS,
        fn=_execute,
    )
