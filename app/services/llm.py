"""LLMService abstraction — plug-and-play billing reconciliation backend.

ADR-001 §2: a single ``LLM_SERVICE_PROVIDER`` env var selects the backend
at deploy time with zero code changes. Production uses DeepSeek V4 Pro
(air-gapped, self-hosted within the Fly.io HIPAA boundary). Dev/staging
uses Azure OpenAI (BAA-covered under Microsoft Healthcare BAA).

The application calls ``llm_service.complete(prompt)`` — it never imports
a specific backend implementation directly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


class LLMProvider(str, Enum):
    DEEPSEEK = "deepseek"
    AZURE_OPENAI = "azure_openai"
    ANTHROPIC = "anthropic"


@dataclass
class LLMCompletionResult:
    content: str
    model: str
    finish_reason: str | None = None
    usage: dict = field(default_factory=dict)


class LLMService(ABC):
    @abstractmethod
    async def complete(self, prompt: str, max_tokens: int = 256) -> LLMCompletionResult:
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        raise NotImplementedError


class DeepSeekLLMService(LLMService):
    """Billing reconciliation LLM running air-gapped within Fly.io boundary.

    ADR-001 §26: model variant, memory requirements, and inference latency
    must be benchmarked before Phase 1D. This stub returns a placeholder.
    """

    def __init__(self, model_id: str = "deepseek-ai/DeepSeek-V4-Pro") -> None:
        self._model_id = model_id

    async def complete(self, prompt: str, max_tokens: int = 256) -> LLMCompletionResult:
        return LLMCompletionResult(
            content="[DeepSeek V4 Pro stub — Phase 1D billing reconciliation not yet built]",
            model=self._model_id,
        )

    async def close(self) -> None:
        pass


class AzureOpenAILLMService(LLMService):
    """Dev/staging billing reconciliation via Azure OpenAI GPT-4o-mini.

    Covered under Microsoft Healthcare BAA. Stripped PHI only — never
    send client names, DOBs, or addresses in the prompt.
    """

    def __init__(self, deployment_name: str = "gpt-4o-mini") -> None:
        self._deployment_name = deployment_name

    async def complete(self, prompt: str, max_tokens: int = 256) -> LLMCompletionResult:
        return LLMCompletionResult(
            content="[Azure OpenAI stub — Phase 1D billing reconciliation not yet built]",
            model=self._deployment_name,
        )

    async def close(self) -> None:
        pass


class AnthropicLLMService(LLMService):
    """Billing reconciliation via Anthropic Claude (BAA-covered).

    Alternative dev/staging backend. Same PHI-stripping rules apply.
    """

    def __init__(self, model_id: str = "claude-sonnet-4-20250514") -> None:
        self._model_id = model_id

    async def complete(self, prompt: str, max_tokens: int = 256) -> LLMCompletionResult:
        return LLMCompletionResult(
            content="[Anthropic Claude stub — Phase 1D billing reconciliation not yet built]",
            model=self._model_id,
        )

    async def close(self) -> None:
        pass


def create_llm_service(provider: str = "") -> LLMService:
    provider = provider or LLMProvider.DEEPSEEK.value
    if provider == LLMProvider.DEEPSEEK.value:
        return DeepSeekLLMService()
    if provider == LLMProvider.AZURE_OPENAI.value:
        return AzureOpenAILLMService()
    if provider == LLMProvider.ANTHROPIC.value:
        return AnthropicLLMService()
    raise ValueError(
        f"Unrecognized LLM_SERVICE_PROVIDER: {provider!r}. "
        f"Must be one of: deepseek, azure_openai, anthropic. "
        f"Silent fallback is prohibited — misconfiguration is a PHI risk."
    )
