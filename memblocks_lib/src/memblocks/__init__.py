"""memBlocks - Intelligent modular memory management system for LLMs.

Public API surface — import from here for convenience:

    from memblocks import MemBlocksClient, MemBlocksConfig
    from memblocks.models import MemoryBlock, SemanticMemoryUnit, CoreMemoryUnit
    from memblocks.llm.base import LLMProvider
    from memblocks.llm.groq_provider import GroqLLMProvider
    from memblocks.prompts import PS1_SEMANTIC_PROMPT
"""

__version__ = "0.1.0"

# Core entry-point (import last to avoid circular issues — client imports all others)
from memblocks.config import MemBlocksConfig
from memblocks.client import MemBlocksClient

# LLM abstractions
from memblocks.llm.base import LLMProvider
from memblocks.llm.groq_provider import GroqLLMProvider

# Key model types users commonly type-hint against
from memblocks.models import (
    MemoryBlock,
    MemoryBlockMetaData,
    SemanticMemoryUnit,
    CoreMemoryUnit,
    ResourceMemoryUnit,
    MemoryOperation,
)

__all__ = [
    "__version__",
    # Client
    "MemBlocksClient",
    "MemBlocksConfig",
    # LLM
    "LLMProvider",
    "GroqLLMProvider",
    # Models
    "MemoryBlock",
    "MemoryBlockMetaData",
    "SemanticMemoryUnit",
    "CoreMemoryUnit",
    "ResourceMemoryUnit",
    "MemoryOperation",
]
