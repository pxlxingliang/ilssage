import asyncio
from typing import AsyncIterator

from backend.agents import create_agent
from backend.deps import get_behavior, get_llm_service, get_session_service
from backend.core.context import WorkspaceContext
from backend.core.events import AgentEvent, AgentEventType
from backend.services.title_service import generate_title


async def stream_chat(
    session_id: str,
    user_content: str,
    *,
    model_id: str = "",
) -> AsyncIterator[AgentEvent]:
    """
    Unified chat streaming orchestrator.

    Handles: message history building, agent creation & streaming,
    post-stream persistence, auto title generation.

    Yields AgentEvent for each streaming step; callers handle UI rendering.

    Cancellation: callers should cancel the asyncio task wrapping this coroutine.
    Partial output is persisted on cancellation.
    """
    sess = get_session_service()
    llm = get_llm_service()

    if not sess.get_session(session_id):
        raise ValueError(f"Session {session_id} not found")

    messages = sess.build_chat_history(session_id)
    messages.append({"role": "user", "content": user_content})
    sess.add_message(session_id, "user", user_content)

    agent = _create_agent()
    provider = llm.get_provider(model_id or None)

    text_accum: list[str] = []
    reasoning_accum: list[str] = []
    tool_calls: list[dict] = []
    done_usage: dict = {}
    done_received = False
    persisted = False
    cancelled = False

    try:
        async for event in agent.stream_run(messages, provider, session_id=session_id):
            yield event

            if event.type == AgentEventType.CONTENT_CHUNK:
                text_accum.append(event.data.get("text", ""))

            elif event.type == AgentEventType.REASONING_CHUNK:
                reasoning_accum.append(event.data.get("text", ""))

            elif event.type == AgentEventType.TOOL_CALL_START:
                tool_calls.append({
                    "id": event.data.get("tool_call_id", ""),
                    "type": "function",
                    "function": {
                        "name": event.data.get("tool_name", ""),
                        "arguments": event.data.get("args", ""),
                    },
                })

            elif event.type == AgentEventType.TOOL_CALL_END:
                if tool_calls:
                    tool_calls[-1]["_result"] = event.data.get("result", "")

            elif event.type == AgentEventType.DONE:
                done_usage = event.data.get("usage", {})
                done_received = True

    except asyncio.CancelledError:
        cancelled = True

    except Exception as e:
        yield AgentEvent(
            type=AgentEventType.ERROR,
            data={"message": str(e)},
        )
        return

    finally:
        if not persisted and not done_received and text_accum:
            full_text = "".join(text_accum)
            full_text += "\n\n*(Output truncated by user)*"
            sess.add_message(session_id, "assistant", full_text,
                             reasoning_content="".join(reasoning_accum) or None)
            persisted = True
        if agent:
            agent.cancel()

    if cancelled:
        yield AgentEvent(
            type=AgentEventType.CANCELLED,
            data={"session_id": session_id},
        )
        return

    if not done_received:
        return

    full_text = "".join(text_accum)
    if full_text:
        saved_calls = [
            {k: v for k, v in tc.items() if k != "_result"}
            for tc in tool_calls
        ] if tool_calls else None
        metadata = {}
        if done_usage:
            metadata["token_usage"] = done_usage
        sess.add_message(
            session_id, "assistant", full_text,
            tool_calls=saved_calls,
            metadata=metadata if metadata else None,
            reasoning_content="".join(reasoning_accum) or None,
        )
        persisted = True
        for tc in tool_calls:
            if "_result" in tc:
                sess.add_message(
                    session_id, "tool", tc["_result"],
                    tool_call_id=tc["id"],
                )

    asyncio.create_task(_auto_title(session_id, user_content))


async def run_chat(
    session_id: str,
    user_content: str,
    *,
    model_id: str = "",
) -> str:
    """
    Non-streaming chat orchestrator.

    Same pipeline as stream_chat (message building, agent execution,
    persistence, auto title), but returns the full response string directly.
    """
    sess = get_session_service()
    llm = get_llm_service()
    if not sess.get_session(session_id):
        raise ValueError(f"Session {session_id} not found")

    messages = sess.build_chat_history(session_id)
    messages.append({"role": "user", "content": user_content})
    sess.add_message(session_id, "user", user_content)

    agent = _create_agent()
    provider = llm.get_provider(model_id or None)
    response = await agent.run(messages, provider, session_id=session_id)
    sess.add_message(session_id, "assistant", response)
    asyncio.create_task(generate_chat_title(session_id, user_content))
    return response


def _create_agent():
    behavior = get_behavior()
    return create_agent(
        behavior,
        system_prompt=WorkspaceContext().build_system_prompt(),
    )


async def generate_chat_title(session_id: str, user_content: str):
    """
    Auto-generate a title for a session if it's still 'New Chat'.

    Safe to call as a fire-and-forget task (eg. asyncio.create_task).
    """
    sess = get_session_service()
    llm = get_llm_service()
    session = sess.get_session(session_id)
    if not session or session.get("title") != "New Chat":
        return
    try:
        title = await generate_title(user_content, llm)
        if title:
            sess.update_session(session_id, title=title)
    except Exception:
        pass


async def _auto_title(session_id: str, user_content: str):
    await generate_chat_title(session_id, user_content)
