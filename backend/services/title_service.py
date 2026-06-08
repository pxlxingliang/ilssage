from typing import Optional

TITLE_PROMPT = (
    'Generate a short, concise title (1-6 words) for a conversation '
    'that starts with the following user message. Reply with ONLY the '
    'title text, no quotes, no explanation:\n\n'
    'User: "{content}"\n\nTitle:'
)


async def generate_title(content: str, llm_service) -> Optional[str]:
    if not content or not llm_service:
        print(f"[generate_title] SKIP: content={bool(content)}, llm={bool(llm_service)}")
        return None

    trimmed = content.strip()
    if len(trimmed) > 1000:
        trimmed = trimmed[:1000]

    safe_content = trimmed.replace("{", "{{").replace("}", "}}")

    messages = [
        {"role": "system", "content": "You generate short conversation titles."},
        {"role": "user", "content": TITLE_PROMPT.format(content=safe_content)},
    ]

    try:
        result = await llm_service.ainvoke(
            messages,
            temperature=0.3,
            max_tokens=50,
            thinking=False,
        )
        print(f"[generate_title] LLM response: {result!r}")
        title = result.strip().strip('"').strip("'")
        if not title or len(title) > 80:
            print(f"[generate_title] REJECTED: title={title!r}, len={len(title)}")
            return None
        print(f"[generate_title] SUCCESS: {title!r}")
        return title
    except Exception as e:
        print(f"[generate_title] EXCEPTION: {type(e).__name__}: {e}")
        raise
