from abc import ABC, abstractmethod
from typing import Iterator, List, Dict, Any, Optional, AsyncIterator

from openai import OpenAI, AsyncOpenAI

THINKING_BASE_URLS = {"https://api.deepseek.com"}


class ProviderUsage:
    def __init__(
        self,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
    ):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens

    def to_dict(self) -> Dict[str, int]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


class LLMProvider(ABC):
    @abstractmethod
    def invoke(self, messages: List[Dict], **kwargs) -> str:
        ...

    @abstractmethod
    def stream_invoke(self, messages: List[Dict], **kwargs) -> Iterator[str]:
        ...

    @abstractmethod
    async def ainvoke(self, messages: List[Dict], **kwargs) -> str:
        ...

    @abstractmethod
    async def astream_invoke(
        self, messages: List[Dict], **kwargs
    ) -> AsyncIterator[str]:
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...

    @property
    @abstractmethod
    def context_limit(self) -> int:
        ...

    @property
    @abstractmethod
    def last_usage(self) -> Optional[ProviderUsage]:
        ...


class OpenAICompatibleProvider(LLMProvider):
    def __init__(
        self,
        api_key: str,
        base_url: Optional[str],
        model_name: str,
        context_limit: int = 128000,
    ):
        self._model_name = model_name
        self._context_limit = context_limit
        self._base_url = (base_url or "").rstrip("/")
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.async_client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._last_usage: Optional[ProviderUsage] = None
        self._last_reasoning: Optional[str] = None

    @property
    def is_thinking(self) -> bool:
        return self._base_url in THINKING_BASE_URLS

    def _build_create_kwargs(self, kwargs: dict) -> dict:
        if not self.is_thinking:
            return kwargs
        merged = {"reasoning_effort": "high",
                  "extra_body": {"thinking": {"type": "enabled"}}}
        merged.update(kwargs)
        return merged

    def invoke(self, messages: List[Dict], **kwargs) -> str:
        resp = self.client.chat.completions.create(
            model=self._model_name, messages=messages,
            **self._build_create_kwargs(kwargs),
        )
        if resp.usage:
            self._last_usage = ProviderUsage(
                prompt_tokens=resp.usage.prompt_tokens,
                completion_tokens=resp.usage.completion_tokens,
                total_tokens=resp.usage.total_tokens,
            )
        msg = resp.choices[0].message
        if self.is_thinking:
            self._last_reasoning = getattr(msg, "reasoning_content", None)
        return msg.content or ""

    def stream_invoke(self, messages: List[Dict], **kwargs) -> Iterator[str]:
        stream_kwargs = {**kwargs}
        if "stream_options" not in stream_kwargs:
            stream_kwargs["stream_options"] = {"include_usage": True}
        stream = self.client.chat.completions.create(
            model=self._model_name, messages=messages, stream=True,
            **self._build_create_kwargs(stream_kwargs),
        )
        reasoning_parts: list[str] = []
        for chunk in stream:
            if chunk.usage:
                self._last_usage = ProviderUsage(
                    prompt_tokens=chunk.usage.prompt_tokens or 0,
                    completion_tokens=chunk.usage.completion_tokens or 0,
                    total_tokens=chunk.usage.total_tokens or 0,
                )
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                reasoning_parts.append(delta.reasoning_content)
            if delta.content:
                yield delta.content
        if reasoning_parts:
            self._last_reasoning = "".join(reasoning_parts)

    async def ainvoke(self, messages: List[Dict], **kwargs) -> str:
        resp = await self.async_client.chat.completions.create(
            model=self._model_name, messages=messages,
            **self._build_create_kwargs(kwargs),
        )
        if resp.usage:
            self._last_usage = ProviderUsage(
                prompt_tokens=resp.usage.prompt_tokens,
                completion_tokens=resp.usage.completion_tokens,
                total_tokens=resp.usage.total_tokens,
            )
        msg = resp.choices[0].message
        if self.is_thinking:
            self._last_reasoning = getattr(msg, "reasoning_content", None)
        return msg.content or ""

    async def astream_invoke(
        self, messages: List[Dict], **kwargs
    ) -> AsyncIterator[str]:
        stream_kwargs = {**kwargs}
        if "stream_options" not in stream_kwargs:
            stream_kwargs["stream_options"] = {"include_usage": True}
        stream = await self.async_client.chat.completions.create(
            model=self._model_name, messages=messages, stream=True,
            **self._build_create_kwargs(stream_kwargs),
        )
        reasoning_parts: list[str] = []
        async for chunk in stream:
            if chunk.usage:
                self._last_usage = ProviderUsage(
                    prompt_tokens=chunk.usage.prompt_tokens or 0,
                    completion_tokens=chunk.usage.completion_tokens or 0,
                    total_tokens=chunk.usage.total_tokens or 0,
                )
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                reasoning_parts.append(delta.reasoning_content)
            if delta.content:
                yield delta.content
        if reasoning_parts:
            self._last_reasoning = "".join(reasoning_parts)

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def context_limit(self) -> int:
        return self._context_limit

    @property
    def last_usage(self) -> Optional[ProviderUsage]:
        return self._last_usage
