"""OpenRouterLLMProvider — LLMProvider implementation using LangChain + OpenRouter."""

from typing import Any, Dict, List, Optional, Type, TYPE_CHECKING

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

from memblocks.llm.base import LLMProvider
from memblocks.logger import get_logger

if TYPE_CHECKING:
    from memblocks.config import MemBlocksConfig

logger = get_logger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterLLMProvider(LLMProvider):
    """
    ``LLMProvider`` implementation using ``langchain_openai.ChatOpenAI``
    configured for OpenRouter's API.

    Supports OpenRouter's model fallback feature: provide an ordered list of
    fallback model IDs via ``config.openrouter_fallback_models``. If the
    primary model (``config.llm_model``) fails due to downtime, rate-limiting,
    or content moderation, OpenRouter will automatically try each fallback in
    order before returning an error.

    The ``models`` array is sent in the request body via ``model_kwargs``,
    as required by OpenRouter's API when using an OpenAI-compatible client.
    """

    def __init__(self, config: "MemBlocksConfig") -> None:
        """
        Args:
            config: Library configuration. Reads:
                - ``openrouter_api_key``        — required
                - ``llm_model``                 — primary model
                - ``llm_convo_temperature``
                - ``openrouter_fallback_models`` — ordered fallback model IDs
                - ``openrouter_enable_thinking`` — enable reasoning/thinking

        Raises:
            ValueError: If ``config.openrouter_api_key`` is not set.
        """
        api_key = config.openrouter_api_key
        if not api_key:
            raise ValueError(
                "OPENROUTER_API_KEY not found — set it in .env or pass to MemBlocksConfig"
            )

        self._api_key: str = api_key
        self._model: str = config.llm_model
        self._default_temperature: float = config.llm_convo_temperature
        self._fallback_models: List[str] = config.openrouter_fallback_models_list
        self._enable_thinking: bool = config.openrouter_enable_thinking

        if self._fallback_models:
            logger.debug(
                "OpenRouter fallback models configured: %s",
                self._fallback_models,
            )
        if self._enable_thinking:
            logger.debug("OpenRouter thinking/reasoning enabled")

        # Arize instrumentation — conditional, inside constructor, not at module level.
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
                logger.warning(
                    "Arize/openinference packages not installed — monitoring disabled."
                )
        else:
            logger.debug(
                "Arize monitoring disabled (ARIZE_SPACE_ID / ARIZE_API_KEY not set)"
            )

    def _get_model_kwargs(self) -> Dict[str, Any]:
        """
        Build extra request-body kwargs for OpenRouter.

        Includes:
        - ``models``: ordered fallback model list (if configured)
        - ``reasoning``: enables extended thinking (if configured)

        Both are sent as extra body fields via ``model_kwargs``.
        """
        kwargs: Dict[str, Any] = {}
        return kwargs

    def _build_llm(self, temperature: float) -> ChatOpenAI:
        """Instantiate a ``ChatOpenAI`` client pointed at OpenRouter."""
        return ChatOpenAI(
            model=self._model,
            temperature=temperature,
            api_key=self._api_key,
            base_url=OPENROUTER_BASE_URL,
            reasoning={"enabled": self._enable_thinking},
            extra_body={"models": self._fallback_models}
            if self._fallback_models
            else None,
            model_kwargs=self._get_model_kwargs(),
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
        Create a LangChain structured-output chain using OpenRouter.

        If ``openrouter_fallback_models`` is set, the ``models`` fallback array
        is included in every request so OpenRouter can automatically failover.

        Args:
            system_prompt: System-level prompt string.
            pydantic_model: Pydantic v2 model class for output parsing.
            temperature: Sampling temperature.

        Returns:
            LangChain ``Runnable`` accepting ``{"input": str}`` and returning
            a ``pydantic_model`` instance.
        """
        llm = self._build_llm(temperature)

        structured_llm = llm.with_structured_output(
            pydantic_model,
            method="json_mode",
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

        If ``openrouter_fallback_models`` is set, OpenRouter will try each
        fallback model in order if the primary model is unavailable.

        Args:
            messages: Conversation history as ``[{"role": ..., "content": ...}, ...]``.
            temperature: Override temperature. Defaults to
                         ``config.llm_convo_temperature`` set in ``__init__``.

        Returns:
            Assistant response text.
        """
        effective_temp = (
            temperature if temperature is not None else self._default_temperature
        )
        llm = self._build_llm(effective_temp)
        response = await llm.ainvoke(messages)
        return response.content
