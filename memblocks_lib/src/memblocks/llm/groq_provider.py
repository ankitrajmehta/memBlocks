"""GroqLLMProvider — default LLMProvider implementation using LangChain + Groq."""

from typing import Any, Dict, List, Optional, Type, TYPE_CHECKING

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

from memblocks.llm.base import LLMProvider

if TYPE_CHECKING:
    from memblocks.config import MemBlocksConfig


class GroqLLMProvider(LLMProvider):
    """
    Default ``LLMProvider`` implementation using ``langchain_groq.ChatGroq``.

    Replaces:
    - ``llm/llm_manager.py`` → ``LLMManager`` singleton (lines 22-103).
    - ``services/background_utils.py`` → ``BackgroundLLMProvider`` (lines
      80-131), which existed only because the singleton could not be safely
      shared across event loops.  With a regular class, share or create
      multiple instances freely.

    Changes from LLMManager:
    - No ``__new__`` singleton pattern.
    - Constructor takes ``MemBlocksConfig`` instead of reading the global
      ``settings`` object (llm_manager.py:39-47).
    - Arize instrumentation moves into ``__init__`` and is **conditional** on
      config values.  The old code ran at module import time
      (llm_manager.py:9-19) using ``settings`` globals — just importing the
      module triggered instrumentation regardless of whether Arize was
      configured.  The new code is opt-in.
    - ``chat()`` replaces ``get_chat_llm() + await llm.ainvoke() + .content``.
    - ``create_structured_chain()`` mirrors llm_manager.py:69-99 exactly.
    """

    def __init__(self, config: "MemBlocksConfig") -> None:
        """
        Args:
            config: Library configuration.  Reads ``groq_api_key``,
                    ``llm_model``, ``llm_convo_temperature``, and optional
                    Arize monitoring fields.

        Raises:
            ValueError: If ``config.groq_api_key`` is not set.
        """
        api_key = config.groq_api_key
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY not found — set it in .env or pass to MemBlocksConfig"
            )

        self._api_key: str = api_key
        self._model: str = config.llm_model
        self._default_temperature: float = config.llm_convo_temperature

        # Arize instrumentation — conditional, inside constructor, not at module level.
        # Replaces the module-level block at llm_manager.py:9-19.
        if config.arize_space_id and config.arize_api_key:
            try:
                from openinference.instrumentation.langchain import (
                    LangChainInstrumentor,
                )
                from arize.otel import register

                tracer_provider = register(
                    space_id=config.arize_space_id,
                    api_key=config.arize_api_key,
                    project_name=config.arize_project_name,
                )
                LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
            except ImportError:
                print(
                    "⚠️  Arize/openinference packages not installed — "
                    "monitoring disabled."
                )
        else:
            print(
                "⚠️  Arize monitoring disabled (ARIZE_SPACE_ID / ARIZE_API_KEY not set)"
            )

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
        Create a LangChain structured-output chain using Groq's native JSON mode.

        Mirrors ``LLMManager.create_structured_chain()`` (llm_manager.py:69-99)
        exactly — same ``json_schema`` method, same ``include_raw=False``, same
        prompt template shape.

        Args:
            system_prompt: System-level prompt string.
            pydantic_model: Pydantic v2 model class for output parsing.
            temperature: Sampling temperature.

        Returns:
            LangChain ``Runnable`` accepting ``{"input": str}`` and returning
            a ``pydantic_model`` instance.
        """
        llm = ChatGroq(
            model=self._model,
            temperature=temperature,
            groq_api_key=self._api_key,
        )

        # Use Groq's native JSON schema mode (not tool calling).
        # include_raw=False → only the parsed Pydantic object is returned.
        structured_llm = llm.with_structured_output(
            pydantic_model,
            method="json_schema",
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

        Replaces (chat_service.py:536-538):
            llm = llm_manager.get_chat_llm(temperature=settings.llm_convo_temperature)
            response = await llm.ainvoke(messages)
            assistant_response = response.content

        Args:
            messages: Conversation history as ``[{"role": ..., "content": ...}, ...]``.
            temperature: Override temperature.  Defaults to
                         ``config.llm_convo_temperature`` set in ``__init__``.

        Returns:
            Assistant response text (``response.content``).
        """
        effective_temp = (
            temperature if temperature is not None else self._default_temperature
        )
        llm = ChatGroq(
            model=self._model,
            temperature=effective_temp,
            groq_api_key=self._api_key,
        )
        response = await llm.ainvoke(messages)
        return response.content
