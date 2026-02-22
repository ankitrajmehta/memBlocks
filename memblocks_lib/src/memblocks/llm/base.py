"""LLMProvider — abstract base class for LLM backends."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel


class LLMProvider(ABC):
    """
    Generic, two-method LLM interface.

    Replaces: ``llm/llm_manager.py`` → ``LLMManager`` singleton, specifically
    the two methods services actually call:
      - ``create_structured_chain()`` (llm_manager.py:69-99)
      - ``get_chat_llm()`` + ``await llm.ainvoke()`` + ``.content``
        (chat_service.py:536-538)

    Design note: An earlier draft had 5 domain-specific abstract methods
    (``extract_semantic_memories``, ``resolve_memory_conflicts``, etc.).
    That was wrong — those are *service* responsibilities.  The LLM interface
    is intentionally generic so any backend (OpenAI, Anthropic, local models,
    test mocks) can implement it without understanding memBlocks internals.

    Services compose prompts and call these two methods.
    """

    @abstractmethod
    def create_structured_chain(
        self,
        system_prompt: str,
        pydantic_model: Type[BaseModel],
        temperature: float = 0.0,
    ) -> Any:
        """
        Return a runnable chain that takes ``{"input": str}`` and returns
        an instance of ``pydantic_model``.

        Must support: ``result = await chain.ainvoke({"input": user_input})``

        Replaces: ``LLMManager.create_structured_chain()`` (llm_manager.py:69-99).

        Called by:
        - ``SemanticMemoryService`` — PS1 extraction
          (``PS1_SEMANTIC_PROMPT`` + ``SemanticMemoriesOutput``)
        - ``SemanticMemoryService`` — PS2 conflict resolution
          (``PS2_MEMORY_UPDATE_PROMPT`` + ``PS2MemoryUpdateOutput``)
        - ``CoreMemoryService`` — core memory extraction
          (``CORE_MEMORY_PROMPT`` + ``CoreMemoryOutput``)
        - ``MemoryPipeline`` — recursive summary generation
          (``SUMMARY_SYSTEM_PROMPT`` + ``SummaryOutput``)

        Args:
            system_prompt: System-level prompt string.
            pydantic_model: Pydantic v2 model class for structured output
                            parsing.
            temperature: Sampling temperature (0.0 = deterministic).

        Returns:
            A LangChain-compatible ``Runnable`` (or equivalent) that accepts
            ``{"input": str}`` and returns a ``pydantic_model`` instance.
        """
        ...

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
    ) -> str:
        """
        Send a list of ``{"role": ..., "content": ...}`` messages and return
        the assistant's response as a plain string.

        Replaces:
            llm = llm_manager.get_chat_llm(temperature=settings.llm_convo_temperature)
            response = await llm.ainvoke(messages)   # chat_service.py:536-537
            assistant_response = response.content      # chat_service.py:538

        Called by: ``ChatEngine.send_message()`` for the main conversation turn.

        Args:
            messages: Conversation history as a list of role/content dicts.
            temperature: Override temperature for this call.  If None the
                         implementation uses its configured default.

        Returns:
            The assistant's response text.
        """
        ...
