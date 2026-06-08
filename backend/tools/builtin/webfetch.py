import re
import urllib.request
import urllib.error
import ssl

from backend.tools.registry import ToolInfo

DESCRIPTION = """\
Fetches content from a specified URL and processes into markdown.
- Fetches content from a specified URL
- Takes a URL and optional format as input
- Fetches the URL content, converts to requested format (markdown by default)
- Returns the content in the specified format
- Use this tool when you need to retrieve and analyze web content

Usage notes:
  - IMPORTANT: if another tool is present that offers better web fetching capabilities, is more targeted to the task, or has fewer restrictions, prefer using that tool instead of this one.
  - The URL must be a fully-formed valid URL
  - HTTP URLs will be automatically upgraded to HTTPS
  - Format options: "markdown" (default), "text", or "html"
  - This tool is read-only and does not modify any files
  - Results may be summarized if the content is very large"""

PARAMETERS = {
    "type": "object",
    "properties": {
        "url": {
            "type": "string",
            "description": "The URL to fetch content from",
        },
        "format": {
            "type": "string",
            "enum": ["text", "markdown", "html"],
            "description": "The format to return the content in (text, markdown, or html). Defaults to markdown.",
            "default": "markdown",
        },
        "timeout": {
            "type": "integer",
            "description": "Optional timeout in seconds (max 120)",
        },
    },
    "required": ["url"],
}

MAX_RESPONSE_SIZE = 5 * 1024 * 1024
DEFAULT_TIMEOUT = 30
MAX_TIMEOUT = 120

_UNWANTED_TAGS = re.compile(
    r"<(script|style|noscript|iframe|object|embed|meta|link)[^>]*>.*?</\1>",
    re.DOTALL | re.IGNORECASE,
)
_TAG_CLEAN = re.compile(r"<[^>]+>")
_WHITESPACE = re.compile(r"\s+")


def _html_to_text(html: str) -> str:
    text = _UNWANTED_TAGS.sub("", html)
    text = _TAG_CLEAN.sub(" ", text)
    text = _WHITESPACE.sub(" ", text)
    return text.strip()


def _html_to_markdown(html: str) -> str:
    text = html

    text = re.sub(r"<h1[^>]*>(.*?)</h1>", r"\n# \1\n", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<h2[^>]*>(.*?)</h2>", r"\n## \1\n", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<h3[^>]*>(.*?)</h3>", r"\n### \1\n", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<h4[^>]*>(.*?)</h4>", r"\n#### \1\n", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<h5[^>]*>(.*?)</h5>", r"\n##### \1\n", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<h6[^>]*>(.*?)</h6>", r"\n###### \1\n", text, flags=re.DOTALL | re.IGNORECASE)

    text = re.sub(r"<strong[^>]*>(.*?)</strong>", r"**\1**", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<b[^>]*>(.*?)</b>", r"**\1**", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<em[^>]*>(.*?)</em>", r"*\1*", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<i[^>]*>(.*?)</i>", r"*\1*", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<code[^>]*>(.*?)</code>", r"`\1`", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<pre[^>]*>(.*?)</pre>", r"\n```\n\1\n```\n", text, flags=re.DOTALL | re.IGNORECASE)

    text = re.sub(r"<a[^>]*href=[\"'](.*?)[\"'][^>]*>(.*?)</a>", r"[\2](\1)", text, flags=re.DOTALL | re.IGNORECASE)

    text = re.sub(r"<li[^>]*>(.*?)</li>", r"- \1\n", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<p[^>]*>", r"\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<br\s*/?>", r"\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", r"", text, flags=re.IGNORECASE)

    text = _UNWANTED_TAGS.sub("", text)
    text = _TAG_CLEAN.sub("", text)
    text = _WHITESPACE.sub(" ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def _execute(url: str, format: str = "markdown", timeout: int = 0) -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    timeout_sec = min(max((timeout or DEFAULT_TIMEOUT), 1), MAX_TIMEOUT)

    ctx = ssl.create_default_context()
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; ILsSage/1.0)",
            "Accept": "text/html,text/plain,text/markdown,*/*",
        },
    )

    try:
        resp = urllib.request.urlopen(req, timeout=timeout_sec, context=ctx)
    except urllib.error.URLError as e:
        return f"Error fetching URL: {e}"
    except Exception as e:
        return f"Error: {e}"

    content_type = resp.headers.get("Content-Type", "")
    content_length = resp.headers.get("Content-Length")
    if content_length and int(content_length) > MAX_RESPONSE_SIZE:
        return "Response too large (exceeds 5MB limit)"

    try:
        body = resp.read(MAX_RESPONSE_SIZE + 1)
    except Exception as e:
        return f"Error reading response: {e}"

    if len(body) > MAX_RESPONSE_SIZE:
        return "Response too large (exceeds 5MB limit)"

    try:
        text = body.decode("utf-8", errors="replace")
    except Exception:
        text = body.decode("latin-1", errors="replace")

    is_html = "text/html" in content_type or text.strip().startswith("<")

    if format == "text":
        output = _html_to_text(text) if is_html else text
    elif format == "markdown":
        output = _html_to_markdown(text) if is_html else text
    else:
        output = text

    return output


def create_webfetch_tool() -> ToolInfo:
    return ToolInfo(
        name="webfetch",
        description=DESCRIPTION,
        parameters=PARAMETERS,
        fn=_execute,
    )
