from typing import Optional

TITLE_PROMPT = (
    'Generate a short, concise title (1-6 words) for a conversation '
    'that starts with the following user message. Reply with ONLY the '
    'title text, no quotes, no explanation:\n\n'
    'User: "{content}"\n\nTitle:'
)


async def generate_title(content: str, llm_service) -> Optional[str]:
    if not content or not llm_service:
        return _fallback_title(content)

    trimmed = content.strip()
    if len(trimmed) > 200:
        trimmed = trimmed[:200]

    messages = [
        {"role": "system", "content": "You generate short conversation titles."},
        {"role": "user", "content": TITLE_PROMPT.format(content=trimmed)},
    ]

    try:
        result = await llm_service.ainvoke(messages, temperature=0.3, max_tokens=20)
        title = result.strip().strip('"').strip("'")
        if title and len(title) <= 80:
            return title
    except Exception:
        pass

    return _fallback_title(content)


def _fallback_title(content: Optional[str]) -> Optional[str]:
    if not content:
        return None
    title = content.strip().replace("\n", " ").replace("\r", "")
    if len(title) > 10:
        title = title[:10].rstrip() + "…"
    return title or None
