"""AI Provider - Unified interface for Cloud and Embedded AI models."""

import os
import json
from typing import Optional, Dict, Any, List
from pathlib import Path
import structlog

logger = structlog.get_logger(__name__)

# Model ID mapping - maps friendly names to actual API model IDs
MODEL_MAPPING = {
    # Anthropic
    "claude-sonnet-4": "claude-sonnet-4-20250514",
    "claude-sonnet-4-5": "claude-sonnet-4-5-20250929",
    "claude-haiku-3-5": "claude-3-5-haiku-20241022",
    "claude-opus-4": "claude-opus-4-20250514",
    # OpenAI
    "gpt-4o": "gpt-4o",
    "gpt-4o-mini": "gpt-4o-mini",
    "gpt-4-turbo": "gpt-4-turbo",
    # Embedded
    "embedded": "qwen2.5-1.5b-instruct",
    "local": "qwen2.5-1.5b-instruct",
}

# Cost per 1M tokens (USD)
MODEL_COSTS = {
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
    "claude-sonnet-4-5-20250929": {"input": 3.0, "output": 15.0},
    "claude-3-5-haiku-20241022": {"input": 0.25, "output": 1.25},
    "claude-opus-4-20250514": {"input": 15.0, "output": 75.0},
    "gpt-4o": {"input": 2.5, "output": 10.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.6},
    "gpt-4-turbo": {"input": 10.0, "output": 30.0},
    "qwen2.5-1.5b-instruct": {"input": 0.0, "output": 0.0},
}


class EmbeddedAI:
    """Local AI using llama-cpp-python."""
    
    def __init__(self, model_path: str):
        self.model_path = model_path
        self._llm = None
        self._loaded = False
    
    def _load_model(self):
        """Lazy load the model."""
        if self._loaded:
            return
        
        try:
            from llama_cpp import Llama
            
            logger.info("Loading embedded AI model", path=self.model_path)
            self._llm = Llama(
                model_path=self.model_path,
                n_ctx=4096,
                n_threads=4,
                n_batch=512,
                verbose=False,
            )
            self._loaded = True
            logger.info("Embedded AI model loaded successfully")
        except ImportError:
            logger.error("llama-cpp-python not installed")
            raise
        except Exception as e:
            logger.error("Failed to load embedded model", error=str(e))
            raise
    
    async def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """Generate completion using local model."""
        self._load_model()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = self._llm.create_chat_completion(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=["<|im_end|>", "<|endoftext|>"],
            )
            
            content = response["choices"][0]["message"]["content"]
            usage = response.get("usage", {})
            
            return {
                "content": content,
                "model": "qwen2.5-1.5b-instruct",
                "provider": "embedded",
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
                "cost_usd": 0.0,
            }
        except Exception as e:
            logger.error("Embedded AI generation failed", error=str(e))
            raise


class AIProvider:
    """Unified AI provider supporting Anthropic, OpenAI, Ollama, and Embedded models."""
    
    def __init__(
        self,
        anthropic_api_key: str = None,
        openai_api_key: str = None,
        ollama_url: str = None,
        embedded_model_path: str = None,
    ):
        self.anthropic_api_key = anthropic_api_key
        self.openai_api_key = openai_api_key
        self.ollama_url = ollama_url
        
        if embedded_model_path is None:
            embedded_model_path = "/app/data/models/qwen2.5-1.5b-instruct.Q4_K_M.gguf"
        self.embedded_model_path = embedded_model_path
        
        self._anthropic_client = None
        self._openai_client = None
        self._embedded_ai = None
    
    @property
    def has_anthropic(self) -> bool:
        return bool(self.anthropic_api_key)
    
    @property
    def has_openai(self) -> bool:
        return bool(self.openai_api_key)
    
    @property
    def has_ollama(self) -> bool:
        return bool(self.ollama_url)
    
    @property
    def has_embedded(self) -> bool:
        return os.path.exists(self.embedded_model_path)
    
    def get_available_providers(self) -> List[str]:
        """Get list of available providers."""
        providers = []
        if self.has_anthropic:
            providers.append("anthropic")
        if self.has_openai:
            providers.append("openai")
        if self.has_ollama:
            providers.append("ollama")
        if self.has_embedded:
            providers.append("embedded")
        return providers
    
    def _resolve_model(self, model: str) -> str:
        """Resolve friendly model name to actual model ID."""
        return MODEL_MAPPING.get(model, model)
    
    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for API usage."""
        costs = MODEL_COSTS.get(model, {"input": 0, "output": 0})
        input_cost = (input_tokens / 1_000_000) * costs["input"]
        output_cost = (output_tokens / 1_000_000) * costs["output"]
        return round(input_cost + output_cost, 6)
    
    async def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        model: str = None,
        provider: str = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """Generate completion from the best available provider."""
        if not provider:
            if self.has_anthropic:
                provider = "anthropic"
            elif self.has_openai:
                provider = "openai"
            elif self.has_embedded:
                provider = "embedded"
            elif self.has_ollama:
                provider = "ollama"
            else:
                raise ValueError("No AI provider available")
        
        if provider == "anthropic":
            return await self._generate_anthropic(prompt, system_prompt, model, max_tokens, temperature)
        elif provider == "openai":
            return await self._generate_openai(prompt, system_prompt, model, max_tokens, temperature)
        elif provider == "embedded":
            return await self._generate_embedded(prompt, system_prompt, max_tokens, temperature)
        elif provider == "ollama":
            return await self._generate_ollama(prompt, system_prompt, model, max_tokens, temperature)
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    async def _generate_anthropic(
        self,
        prompt: str,
        system_prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> Dict[str, Any]:
        """Generate using Anthropic Claude."""
        if not self.has_anthropic:
            raise ValueError("Anthropic API key not configured")
        
        import anthropic
        
        if self._anthropic_client is None:
            self._anthropic_client = anthropic.AsyncAnthropic(api_key=self.anthropic_api_key)
        
        model = self._resolve_model(model or "claude-sonnet-4")
        
        try:
            kwargs = {
                "model": model,
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system_prompt:
                kwargs["system"] = system_prompt
            if temperature != 1.0:
                kwargs["temperature"] = temperature
            
            response = await self._anthropic_client.messages.create(**kwargs)
            
            content = response.content[0].text
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            
            return {
                "content": content,
                "model": model,
                "provider": "anthropic",
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "cost_usd": self._calculate_cost(model, input_tokens, output_tokens),
            }
        except Exception as e:
            logger.error("Anthropic API error", error=str(e))
            raise
    
    async def _generate_openai(
        self,
        prompt: str,
        system_prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> Dict[str, Any]:
        """Generate using OpenAI."""
        if not self.has_openai:
            raise ValueError("OpenAI API key not configured")
        
        import openai
        
        if self._openai_client is None:
            self._openai_client = openai.AsyncOpenAI(api_key=self.openai_api_key)
        
        model = self._resolve_model(model or "gpt-4o-mini")
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = await self._openai_client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            
            content = response.choices[0].message.content
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            
            return {
                "content": content,
                "model": model,
                "provider": "openai",
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "cost_usd": self._calculate_cost(model, input_tokens, output_tokens),
            }
        except Exception as e:
            logger.error("OpenAI API error", error=str(e))
            raise
    
    async def _generate_embedded(
        self,
        prompt: str,
        system_prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> Dict[str, Any]:
        """Generate using embedded local model."""
        if not self.has_embedded:
            raise ValueError(f"Embedded model not found at {self.embedded_model_path}")
        
        if self._embedded_ai is None:
            self._embedded_ai = EmbeddedAI(self.embedded_model_path)
        
        return await self._embedded_ai.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    
    async def _generate_ollama(
        self,
        prompt: str,
        system_prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> Dict[str, Any]:
        """Generate using Ollama."""
        if not self.has_ollama:
            raise ValueError("Ollama URL not configured")
        
        import httpx
        
        model = model or "llama3.2"
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/chat",
                    json={
                        "model": model,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "num_predict": max_tokens,
                            "temperature": temperature,
                        },
                    },
                )
                response.raise_for_status()
                data = response.json()
                
                return {
                    "content": data.get("message", {}).get("content", ""),
                    "model": model,
                    "provider": "ollama",
                    "input_tokens": data.get("prompt_eval_count", 0),
                    "output_tokens": data.get("eval_count", 0),
                    "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
                    "cost_usd": 0.0,
                }
        except Exception as e:
            logger.error("Ollama API error", error=str(e))
            raise
    
    async def generate_json(
        self,
        prompt: str,
        system_prompt: str = None,
        model: str = None,
        provider: str = None,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """Generate and parse JSON response."""
        json_system = (system_prompt or "") + "\n\nRespond only with valid JSON. No markdown, no explanation."
        
        result = await self.generate(
            prompt=prompt,
            system_prompt=json_system,
            model=model,
            provider=provider,
            max_tokens=max_tokens,
            temperature=0.3,
        )
        
        content = result["content"]
        
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        try:
            parsed = json.loads(content.strip())
            result["parsed"] = parsed
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse AI response as JSON", error=str(e))
            result["parsed"] = None
            result["parse_error"] = str(e)
        
        return result
