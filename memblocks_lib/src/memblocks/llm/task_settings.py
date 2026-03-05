"""LLMTaskSettings and LLMSettings — per-task LLM configuration.

These models let callers assign a different LLM provider, model, and
temperature to each distinct task the library performs.

Typical usage:

    from memblocks import MemBlocksConfig
    from memblocks.llm.task_settings import LLMSettings, LLMTaskSettings

    config = MemBlocksConfig(
        openrouter_api_key="...",
        groq_api_key="...",
        llm_settings=LLMSettings(
            # Required global fallback — used for any task not explicitly set
            default=LLMTaskSettings(
                provider="openrouter",
                model="meta-llama/llama-4-maverick-17b-128e-instruct",
                temperature=0.0,
            ),
            # Use a cheap/fast model for retrieval (query expansion + re-ranking)
            retrieval=LLMTaskSettings(
                provider="groq",
                model="llama-3.1-8b-instant",
                temperature=0.4,
            ),
            # Use a smarter model for PS2 conflict resolution
            ps2_conflict_resolution=LLMTaskSettings(
                provider="openrouter",
                model="anthropic/claude-3.5-sonnet",
                temperature=0.0,
            ),
            # Conversational chat with higher temperature
            conversation=LLMTaskSettings(
                provider="openrouter",
                model="openai/gpt-4o",
                temperature=0.7,
            ),
        ),
    )

When ``llm_settings`` is ``None`` in ``MemBlocksConfig``, the client
auto-constructs an ``LLMSettings`` from the flat legacy fields
(``llm_provider_name``, ``llm_model``, per-task temperature fields) so
existing code continues to work unchanged.

OpenRouter-specific fields (``fallback_models``, ``enable_thinking``) are
stored on ``LLMTaskSettings`` but are silently ignored by Groq and Gemini
providers.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class LLMTaskSettings(BaseModel):
    """Settings for a single LLM task.

    Attributes:
        provider: LLM provider name. One of ``"groq"``, ``"gemini"``,
            ``"openrouter"``.
        model: Model identifier string (provider-specific format).
        temperature: Sampling temperature for this task.
        fallback_models: Ordered list of fallback model IDs tried in order
            if the primary model fails.  **OpenRouter only** — ignored by
            Groq and Gemini providers.
        enable_thinking: Enable extended reasoning/thinking tokens.
            **OpenRouter only** — ignored by Groq and Gemini providers.
    """

    provider: str = Field(
        ...,
        description="LLM provider to use. One of: 'groq', 'gemini', 'openrouter'.",
    )
    model: str = Field(..., description="Model identifier string.")
    temperature: float = Field(0.0, description="Sampling temperature.")
    # OpenRouter-specific — silently ignored by other providers
    fallback_models: List[str] = Field(
        default_factory=list,
        description=(
            "Ordered fallback model IDs tried if the primary model fails. "
            "OpenRouter only — ignored by Groq and Gemini."
        ),
    )
    enable_thinking: bool = Field(
        False,
        description=(
            "Enable extended reasoning/thinking tokens. "
            "OpenRouter only — ignored by Groq and Gemini."
        ),
    )


class LLMSettings(BaseModel):
    """Per-task LLM configuration container.

    Each optional task field overrides the ``default`` for that specific task.
    Set a field to ``None`` (or omit it) to fall back to ``default``.

    Tasks:
        default:                  Required. Fallback for any task not explicitly set.
        conversation:             Main conversational chat turn.
        ps1_semantic_extraction:  PS1 — extract structured memories from conversation.
        ps2_conflict_resolution:  PS2 — deduplicate / resolve conflicts in vector store.
        retrieval:                Query enhancement (HyDE + expansion) AND re-ranking.
        core_memory_extraction:   Update the persona + human core memory paragraphs.
        recursive_summary:        Generate rolling conversation summary.
    """

    default: LLMTaskSettings = Field(
        ...,
        description="Global fallback used for any task without an explicit override.",
    )
    conversation: Optional[LLMTaskSettings] = Field(
        None,
        description="Conversational chat turn (client.llm.chat).",
    )
    ps1_semantic_extraction: Optional[LLMTaskSettings] = Field(
        None,
        description="PS1 semantic memory extraction from conversation window.",
    )
    ps2_conflict_resolution: Optional[LLMTaskSettings] = Field(
        None,
        description="PS2 conflict resolution — ADD/UPDATE/DELETE decisions.",
    )
    retrieval: Optional[LLMTaskSettings] = Field(
        None,
        description="Query enhancement (HyDE + expansion) and re-ranking.",
    )
    core_memory_extraction: Optional[LLMTaskSettings] = Field(
        None,
        description="Core memory extraction — persona and human paragraphs.",
    )
    recursive_summary: Optional[LLMTaskSettings] = Field(
        None,
        description="Recursive summary generation.",
    )

    def for_task(self, task: str) -> LLMTaskSettings:
        """Return the effective ``LLMTaskSettings`` for a named task.

        Falls back to ``self.default`` if the task field is ``None`` or the
        task name is not a known field.

        Args:
            task: One of the task field names (e.g. ``"ps1_semantic_extraction"``).

        Returns:
            The task-specific settings, or ``self.default`` if not set.
        """
        override = getattr(self, task, None)
        return override if override is not None else self.default


__all__ = ["LLMTaskSettings", "LLMSettings"]
