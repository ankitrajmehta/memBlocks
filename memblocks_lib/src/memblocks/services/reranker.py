"""Cohere Re-ranker Service for semantic memory retrieval.

This module provides a high-performance re-ranking service using Cohere's re-rank API
instead of LLM-based re-ranking to reduce latency and improve retrieval accuracy.
"""

import os
from typing import List, Optional, TYPE_CHECKING
from dataclasses import dataclass

from memblocks.logger import get_logger

if TYPE_CHECKING:
    from memblocks.models.units import SemanticMemoryUnit

logger = get_logger(__name__)


@dataclass
class RerankedResult:
    """Result from Cohere re-ranking with relevance score."""
    memory: "SemanticMemoryUnit"
    relevance_score: float
    index: int  # Original index in the input list


class CohereReranker:
    """
    Cohere-based re-ranker for semantic memory retrieval.
    
    Uses Cohere's rerank-english-v3.0 model to re-rank retrieved memories
    based on their relevance to the user's query. This is significantly faster
    and more accurate than LLM-based re-ranking.
    
    Example:
        ```python
        reranker = CohereReranker(api_key="your-api-key")
        reranked_memories = await reranker.rerank(
            query="What is the user's favorite programming language?",
            memories=retrieved_memories,
            top_n=10
        )
        ```
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "rerank-english-v3.0",
    ) -> None:
        """
        Initialize Cohere re-ranker.
        
        Args:
            api_key: Cohere API key. If None, reads from COHERE_API_KEY env var.
            model: Cohere rerank model to use. Default: rerank-english-v3.0 (free tier)
        """
        self._api_key = api_key or os.environ.get("COHERE_API_KEY")
        if not self._api_key:
            raise ValueError(
                "Cohere API key not provided. Set COHERE_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        self._model = model
        self._client = None  # Lazy initialization
        
    def _get_client(self):
        """Lazy initialization of Cohere client."""
        if self._client is None:
            try:
                import cohere
                self._client = cohere.ClientV2(self._api_key)
            except ImportError as e:
                raise ImportError(
                    "Cohere library not installed. Install with: pip install cohere"
                ) from e
        return self._client
    
    async def rerank(
        self,
        query: str,
        memories: List["SemanticMemoryUnit"],
        top_n: Optional[int] = None,
    ) -> List["SemanticMemoryUnit"]:
        """
        Re-rank memories by relevance to the query using Cohere's re-rank API.
        
        Args:
            query: Original user query text.
            memories: List of memory units to re-rank.
            top_n: Number of top results to return. If None, returns all re-ranked memories.
        
        Returns:
            List of memories ordered by relevance (highest first), limited to top_n if specified.
        """
        if not memories:
            logger.debug("No memories to re-rank")
            return []
        
        # Prepare documents for Cohere API
        # Use content as the main text, enriched with keywords and entities
        documents = []
        for memory in memories:
            # Build a rich document representation
            doc_text = memory.content
            
            # Optionally enrich with keywords and entities for better matching
            if memory.keywords:
                doc_text += f"\nKeywords: {', '.join(memory.keywords)}"
            if memory.entities:
                doc_text += f"\nEntities: {', '.join(memory.entities)}"
            
            documents.append(doc_text)
        
        try:
            client = self._get_client()
            
            # Set top_n to len(memories) if not specified to get all results ranked
            effective_top_n = top_n if top_n is not None else len(memories)
            
            logger.debug(
                "Re-ranking %d memories with Cohere (model=%s, top_n=%d)",
                len(memories),
                self._model,
                effective_top_n,
            )
            
            # Call Cohere rerank API
            results = client.rerank(
                model=self._model,
                query=query,
                documents=documents,
                top_n=effective_top_n,
            )
            
            # Map results back to original memories with scores
            reranked_memories: List["SemanticMemoryUnit"] = []
            
            for result in results.results:
                original_idx = result.index
                relevance_score = result.relevance_score
                
                # Get the original memory
                memory = memories[original_idx]
                
                logger.debug(
                    "Memory %s: score=%.3f, content=%s",
                    memory.memory_id[:8] if memory.memory_id else "None",
                    relevance_score,
                    memory.content[:60],
                )
                
                reranked_memories.append(memory)
            
            logger.info(
                "Re-ranked %d memories to %d results for query: %s",
                len(memories),
                len(reranked_memories),
                query[:50],
            )
            
            return reranked_memories
        
        except Exception as e:
            logger.error("Cohere re-ranking failed: %s. Returning original order.", e)
            # Fallback: return original memories (possibly limited to top_n)
            if top_n is not None:
                return memories[:top_n]
            return memories
    
    def rerank_sync(
        self,
        query: str,
        memories: List["SemanticMemoryUnit"],
        top_n: Optional[int] = None,
    ) -> List["SemanticMemoryUnit"]:
        """
        Synchronous version of rerank() for non-async contexts.
        
        Args:
            query: Original user query text.
            memories: List of memory units to re-rank.
            top_n: Number of top results to return. If None, returns all re-ranked memories.
        
        Returns:
            List of memories ordered by relevance (highest first), limited to top_n if specified.
        """
        if not memories:
            logger.debug("No memories to re-rank")
            return []
        
        # Prepare documents for Cohere API
        documents = []
        for memory in memories:
            doc_text = memory.content
            
            if memory.keywords:
                doc_text += f"\nKeywords: {', '.join(memory.keywords)}"
            if memory.entities:
                doc_text += f"\nEntities: {', '.join(memory.entities)}"
            
            documents.append(doc_text)
        
        try:
            client = self._get_client()
            
            effective_top_n = top_n if top_n is not None else len(memories)
            
            logger.debug(
                "Re-ranking %d memories with Cohere (model=%s, top_n=%d)",
                len(memories),
                self._model,
                effective_top_n,
            )
            
            # Call Cohere rerank API (synchronous)
            results = client.rerank(
                model=self._model,
                query=query,
                documents=documents,
                top_n=effective_top_n,
            )
            
            # Map results back to original memories
            reranked_memories: List["SemanticMemoryUnit"] = []
            
            for result in results.results:
                original_idx = result.index
                relevance_score = result.relevance_score
                memory = memories[original_idx]
                
                logger.debug(
                    "Memory %s: score=%.3f, content=%s",
                    memory.memory_id[:8] if memory.memory_id else "None",
                    relevance_score,
                    memory.content[:60],
                )
                
                reranked_memories.append(memory)
            
            logger.info(
                "Re-ranked %d memories to %d results for query: %s",
                len(memories),
                len(reranked_memories),
                query[:50],
            )
            
            return reranked_memories
        
        except Exception as e:
            logger.error("Cohere re-ranking failed: %s. Returning original order.", e)
            if top_n is not None:
                return memories[:top_n]
            return memories


__all__ = ["CohereReranker", "RerankedResult"]
