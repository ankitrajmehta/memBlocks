"""GeminiLLMProvider — LLMProvider implementation using LangChain + Google Gemini."""

from typing import Any, Dict, List, Optional, Type, TYPE_CHECKING

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

from memblocks.llm.base import LLMProvider
from memblocks.logger import get_logger

if TYPE_CHECKING:
    from memblocks.config import MemBlocksConfig
    from memblocks.llm.task_settings import LLMTaskSettings

logger = get_logger(__name__)


class GeminiLLMProvider(LLMProvider):
    """
    ``LLMProvider`` implementation using ``langchain_google_genai.ChatGoogleGenerativeAI``.

    Mirrors the structure of ``GroqLLMProvider`` but uses Google's Gemini API instead.
    Designed to work seamlessly with the existing memBlocks architecture.

    Can be instantiated either from a full ``MemBlocksConfig`` (legacy path)
    or from a bare ``LLMTaskSettings`` + ``api_key`` (per-task path used by
    ``MemBlocksClient`` when ``llm_settings`` is configured).

    Note: ``fallback_models`` and ``enable_thinking`` in ``LLMTaskSettings``
    are OpenRouter-specific and are silently ignored by this provider.
    """

    def __init__(self, config: "MemBlocksConfig") -> None:
        """
        Construct from a full ``MemBlocksConfig``.

        Prefer ``GeminiLLMProvider.from_task_settings()`` when building a
        per-task provider inside ``MemBlocksClient``.

        Args:
            config: Library configuration.  Reads ``gemini_api_key``,
                    ``llm_model``, ``llm_convo_temperature``, and optional
                    Arize monitoring fields.

        Raises:
            ValueError: If ``config.gemini_api_key`` is not set.
        """
        api_key = config.gemini_api_key
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY not found — set it in .env or pass to MemBlocksConfig"
            )

        self._api_key: str = api_key
        self._model: str = config.llm_model
        self._default_temperature: float = config.llm_convo_temperature

        # Arize instrumentation — conditional, inside constructor, not at module level.
        if config.arize_space_id and config.arize_api_key:
            try:
                from openinference.instrumentation.langchain import (
                    LangChainInstrumentor,
                )
                from arize.otel import register
                from opentelemetry import trace

                existing = trace.get_tracer_provider()
                if not hasattr(existing, '_initialized'):
                    tracer_provider = register(
                        space_id=config.arize_space_id,
                        api_key=config.arize_api_key,
                        project_name=config.arize_project_name,
                    )
                    tracer_provider._initialized = True
                    LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
            except ImportError:
                logger.warning(
                    "Arize/openinference packages not installed — monitoring disabled."
                )
        else:
            logger.debug(
                "Arize monitoring disabled (ARIZE_SPACE_ID / ARIZE_API_KEY not set)"
            )

    @classmethod
    def from_task_settings(
        cls,
        task_settings: "LLMTaskSettings",
        api_key: str,
        arize_space_id: Optional[str] = None,
        arize_api_key: Optional[str] = None,
        arize_project_name: str = "memBlocks",
    ) -> "GeminiLLMProvider":
        """Construct a provider directly from ``LLMTaskSettings``.

        This is the preferred path when ``MemBlocksClient`` builds per-task
        providers from ``config.resolved_llm_settings``.

        Args:
            task_settings: Task-specific LLM settings (model, temperature).
                ``fallback_models`` and ``enable_thinking`` are silently ignored.
            api_key: Google Gemini API key.
            arize_space_id: Optional Arize monitoring space ID.
            arize_api_key: Optional Arize monitoring API key.
            arize_project_name: Arize project name.

        Returns:
            Configured ``GeminiLLMProvider`` instance.
        """
        instance = cls.__new__(cls)
        instance._api_key = api_key
        instance._model = task_settings.model
        instance._default_temperature = task_settings.temperature

        if arize_space_id and arize_api_key:
            try:
                from openinference.instrumentation.langchain import (
                    LangChainInstrumentor,
                )
                from arize.otel import register
                from opentelemetry import trace

                existing = trace.get_tracer_provider()
                if not hasattr(existing, '_initialized'):
                    tracer_provider = register(
                        space_id=arize_space_id,
                        api_key=arize_api_key,
                        project_name=arize_project_name,
                    )
                    tracer_provider._initialized = True
                    LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
            except ImportError:
                logger.warning(
                    "Arize/openinference packages not installed — monitoring disabled."
                )
        else:
            logger.debug(
                "Arize monitoring disabled (ARIZE_SPACE_ID / ARIZE_API_KEY not set)"
            )

        return instance

    # ------------------------------------------------------------------
    # LLMProvider implementation
    # ------------------------------------------------------------------

    def create_structured_chain(
        self,
        system_prompt: str,
        pydantic_model: Type[BaseModel],
        temperature: float = 0.0,
    ) -> Any:
        """
        Create a LangChain structured-output chain using Gemini's structured output mode.

        Follows the same pattern as ``GroqLLMProvider.create_structured_chain()``.

        Args:
            system_prompt: System-level prompt string.
            pydantic_model: Pydantic v2 model class for output parsing.
            temperature: Sampling temperature.

        Returns:
            LangChain ``Runnable`` accepting ``{"input": str}`` and returning
            a ``pydantic_model`` instance.
        """
        llm = ChatGoogleGenerativeAI(
            model=self._model,
            temperature=temperature,
            google_api_key=self._api_key,
        )

        # Use Gemini's structured output mode.
        # include_raw=False → only the parsed Pydantic object is returned.
        structured_llm = llm.with_structured_output(
            pydantic_model,
            include_raw=False,
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("user", "{input}"),
            ]
        )

        return prompt | structured_llm

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
    ) -> str:
        """
        Send a conversation and return the assistant's response text.

        Mirrors ``GroqLLMProvider.chat()`` but uses Gemini API.

        Args:
            messages: Conversation history as ``[{"role": ..., "content": ...}, ...]``.
            temperature: Override temperature.  Defaults to
                         ``config.llm_convo_temperature`` set in ``__init__``.

        Returns:
            Assistant response text (extracted from response.content).
        """
        effective_temp = (
            temperature if temperature is not None else self._default_temperature
        )
        llm = ChatGoogleGenerativeAI(
            model=self._model,
            temperature=effective_temp,
            google_api_key=self._api_key,
        )
        response = await llm.ainvoke(messages)

        # Handle Gemini's structured response format
        content = response.content
        if isinstance(content, list):
            # Extract text from list of content parts
            text_parts = []
            for part in content:
                if isinstance(part, dict) and "text" in part:
                    text_parts.append(part["text"])
                elif hasattr(part, "text"):
                    text_parts.append(part.text)
            return "".join(text_parts)

        # Fallback to string content
        return str(content)
