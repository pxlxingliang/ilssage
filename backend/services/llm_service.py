from typing import List, Dict, Optional, Iterator, AsyncIterator
from backend.core.llm import LLMProvider, OpenAICompatibleProvider
from backend.core.config import load_config
from backend.tools.registry import ToolRegistry


class LLMService:
    def __init__(self, config_path: Optional[str] = None,
                 tool_registry: Optional[ToolRegistry] = None,
                 model_id: Optional[str] = None):
        self.config = load_config(config_path)
        self.current_model = model_id or self.config.get("currentModel", "")
        self._providers: Dict[str, LLMProvider] = {}
        self.tool_registry = tool_registry

        if not self.current_model:
            models = self.list_models()
            if models:
                self.current_model = models[0]["id"]

    def get_openai_tools(self) -> List[Dict]:
        if self.tool_registry:
            return self.tool_registry.to_openai_tools()
        return []

    def get_provider(self, model_id: Optional[str] = None) -> LLMProvider:
        model_id = model_id or self.current_model
        if not model_id or "/" not in model_id:
            raise RuntimeError(
                "No model configured. Please set currentModel in "
                "~/.ilssage/config.json or provide a valid model_id."
            )
        if model_id in self._providers:
            return self._providers[model_id]

        provider_name, model_name = model_id.split("/", 1)
        pconf = self.config["providers"][provider_name]
        mconf = pconf["models"][model_name]
        opts = pconf["options"]

        provider = OpenAICompatibleProvider(
            api_key=opts.get("apiKey", ""),
            base_url=opts.get("baseURL"),
            model_name=model_name,
            context_limit=mconf.get("limit", {}).get("context", 128000),
        )
        self._providers[model_id] = provider
        return provider

    def switch_model(self, model_id: str):
        self.current_model = model_id

    def list_models(self) -> List[Dict]:
        models = []
        for pname, pconf in self.config.get("providers", {}).items():
            for mname, mconf in pconf.get("models", {}).items():
                models.append({
                    "id": f"{pname}/{mname}",
                    "name": mconf.get("name", mname),
                    "provider": pconf.get("name", pname),
                    "limit": mconf.get("limit", {}),
                })
        return models

    def get_current_model(self) -> Dict:
        if not self.current_model or "/" not in self.current_model:
            return {"id": "", "name": "No model", "provider": "", "limit": {}}
        try:
            pname, mname = self.current_model.split("/", 1)
            pconf = self.config["providers"][pname]
            mconf = pconf["models"][mname]
            return {
                "id": self.current_model,
                "name": mconf.get("name", mname),
                "provider": pconf.get("name", pname),
                "limit": mconf.get("limit", {}),
            }
        except (KeyError, ValueError):
            return {"id": self.current_model, "name": "Unknown", "provider": "", "limit": {}}

    def invoke(self, messages: List[Dict], *, thinking: Optional[bool] = None, **kwargs) -> str:
        return self.get_provider().invoke(messages, thinking=thinking, **kwargs)

    def stream_invoke(self, messages: List[Dict], *, thinking: Optional[bool] = None, **kwargs) -> Iterator[str]:
        return self.get_provider().stream_invoke(messages, thinking=thinking, **kwargs)

    async def ainvoke(self, messages: List[Dict], *, thinking: Optional[bool] = None, **kwargs) -> str:
        return await self.get_provider().ainvoke(messages, thinking=thinking, **kwargs)

    async def astream_invoke(
        self, messages: List[Dict], *, thinking: Optional[bool] = None, **kwargs
    ) -> AsyncIterator[str]:
        async for chunk in self.get_provider().astream_invoke(
            messages, thinking=thinking, **kwargs
        ):
            yield chunk
