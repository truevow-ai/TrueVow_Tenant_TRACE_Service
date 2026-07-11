"""LLMService abstraction — plug-and-play billing reconciliation backend.

ADR-001 §2 + ADR-003 §4b: ``LLM_SERVICE_PROVIDER`` env var selects
the backend at deploy time with zero code changes.

Primary production: Azure OpenAI GPT-4o-mini (BAA under Microsoft DPA,
~$0.50/month at TRACE volume, no self-hosted infra needed).

DeepSeek V4 Pro self-hosted removed (AD update July 9, 2026):
breakeven at 31-36M tokens/day vs TRACE's 37K — 0.1% of threshold.
DeepSeek V4 Flash via inference API added as cost comparison candidate.

The application calls ``llm_service.complete(prompt)`` — it never
imports a specific backend implementation directly.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


class LLMProvider(str, Enum):
    AZURE_OPENAI = "azure_openai"
    DEEPSEEK_API = "deepseek_api"
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


class DeepSeekAPILLMService(LLMService):
    """DeepSeek V4 Flash via inference API (HIPAA-aligned provider like DeepInfra).

    Cost comparison candidate per AD update July 2026. Not self-hosted — runs
    through a BAA-covered inference provider. 60% cheaper than GPT-4o-mini.
    """

    def __init__(self, model_id: str = "deepseek-ai/DeepSeek-V4-Flash") -> None:
        self._model_id = model_id

    async def complete(self, prompt: str, max_tokens: int = 256) -> LLMCompletionResult:
        return LLMCompletionResult(
            content="[DeepSeek V4 Flash API stub — Phase 1D billing reconciliation not yet built]",
            model=self._model_id,
        )

    async def close(self) -> None:
        pass


class AzureOpenAILLMService(LLMService):
    """Dev/staging billing reconciliation via Azure OpenAI GPT-4o-mini.

    Covered under Microsoft Healthcare BAA. Stripped PHI only — never
    send client names, DOBs, or addresses in the prompt.

    All connection parameters come from environment:
      AZURE_OPENAI_ENDPOINT   — https://your-resource.openai.azure.com/
      AZURE_OPENAI_API_KEY     — Azure API key
      AZURE_OPENAI_DEPLOYMENT  — Deployment name from Azure AI Foundry
    """

    def __init__(self, endpoint: str, api_key: str, deployment: str) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._api_key = api_key
        self._deployment = deployment

    async def complete(self, prompt: str, max_tokens: int = 256) -> LLMCompletionResult:
        return LLMCompletionResult(
            content="[Azure OpenAI stub — Phase 1D billing reconciliation not yet built]",
            model=self._deployment,
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
    provider = provider or os.environ.get("LLM_SERVICE_PROVIDER", LLMProvider.AZURE_OPENAI.value)
    if provider == LLMProvider.AZURE_OPENAI.value:
        return AzureOpenAILLMService(
            endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            deployment=os.environ["AZURE_OPENAI_DEPLOYMENT"],
        )
    if provider == LLMProvider.DEEPSEEK_API.value:
        return DeepSeekAPILLMService()
    if provider == LLMProvider.ANTHROPIC.value:
        return AnthropicLLMService()
    raise ValueError(
        f"Unrecognized LLM_SERVICE_PROVIDER: {provider!r}. "
        f"Must be one of: azure_openai, deepseek_api, anthropic. "
        f"Silent fallback is prohibited — misconfiguration is a PHI risk."
    )
