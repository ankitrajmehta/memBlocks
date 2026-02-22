"""RetrievalResult — structured container returned by Block.retrieve() and friends."""

from typing import List, Optional

from pydantic import BaseModel, Field

from memblocks.models.units import (
    CoreMemoryUnit,
    ResourceMemoryUnit,
    SemanticMemoryUnit,
)


class RetrievalResult(BaseModel):
    """
    Structured container for all memory retrieved for a given query.

    Returned by:
        block.retrieve(query)
        block.core_retrieve()
        block.semantic_retrieve(query)
        block.resource_retrieve(query)

    Use .to_prompt_string() to get a formatted string ready to inject into a
    system prompt, or access .core / .semantic / .resource directly for custom
    formatting.
    """

    core: Optional[CoreMemoryUnit] = Field(
        None,
        description="Core memory (persona + stable human facts). Always fetched in full.",
    )
    semantic: List[SemanticMemoryUnit] = Field(
        default_factory=list,
        description="Semantically relevant memories retrieved via vector search.",
    )
    resource: List[ResourceMemoryUnit] = Field(
        default_factory=list,
        description="Resource memories (documents, links). Empty until implemented.",
    )

    def to_prompt_string(self) -> str:
        """
        Render the retrieval result as a formatted string suitable for
        injection into an LLM system prompt.

        Format:
            <Core Memory>
            [PERSONA]
            ...
            [HUMAN]
            ...
            </Core Memory>

            <Semantic Memories>
            [EVENT] ...
              Keywords: ...
            </Semantic Memories>

        Returns:
            Formatted string, or empty string if nothing was retrieved.
        """
        parts: List[str] = []

        # --- Core memory ---
        if self.core and (self.core.persona_content or self.core.human_content):
            core_lines: List[str] = []
            if self.core.persona_content:
                core_lines.append(f"[PERSONA]\n{self.core.persona_content}")
            if self.core.human_content:
                core_lines.append(f"[HUMAN]\n{self.core.human_content}")
            parts.append(
                "<Core Memory>\n" + "\n\n".join(core_lines) + "\n</Core Memory>"
            )

        # --- Semantic memories ---
        if self.semantic:
            sem_lines = []
            for mem in self.semantic:
                kw = ", ".join(mem.keywords[:5]) if mem.keywords else ""
                entry = f"[{mem.type.upper()}] {mem.content}"
                if kw:
                    entry += f"\n  Keywords: {kw}"
                sem_lines.append(entry)
            parts.append(
                "<Semantic Memories>\n"
                + "\n\n".join(sem_lines)
                + "\n</Semantic Memories>"
            )

        # --- Resource memories (stub — always empty for now) ---
        if self.resource:
            res_lines = [
                f"[{mem.resource_type.upper()}] {mem.content}"
                + (f"\n  Link: {mem.resource_link}" if mem.resource_link else "")
                for mem in self.resource
            ]
            parts.append(
                "<Resource Memories>\n"
                + "\n\n".join(res_lines)
                + "\n</Resource Memories>"
            )

        return "\n\n".join(parts)

    def is_empty(self) -> bool:
        """Return True if no memories were retrieved at all."""
        return (
            (
                self.core is None
                or (not self.core.persona_content and not self.core.human_content)
            )
            and not self.semantic
            and not self.resource
        )


__all__ = ["RetrievalResult"]
