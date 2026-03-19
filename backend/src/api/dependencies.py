"""FastAPI dependency injection — provides a shared MemBlocksClient instance."""

from functools import lru_cache
from typing import Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from memblocks import MemBlocksClient, MemBlocksConfig
from memblocks.llm.task_settings import LLMSettings, LLMTaskSettings


class LLMConfig(BaseModel):
    """LLM configuration with provider and model attributes."""

    provider: str = "groq"
    model: str = "llama-3.1-8b-instant"
    temperature: float = 0.4


class BackendConfig(BaseSettings):
    """Backend-specific configuration extending MemBlocksConfig.

    Uses llm_settings format with provider and model attributes
    so users can easily switch LLM models by changing the config.
    Values are read from environment variables or .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    mongodb_connection_string: str = Field(
        default="mongodb://localhost:27017",
        validation_alias="MONGODB_CONNECTION_STRING",
    )
    mongodb_database_name: str = Field(
        default="memblocks_v2", validation_alias="MONGODB_DATABASE_NAME"
    )

    qdrant_host: str = Field(default="localhost", validation_alias="QDRANT_HOST")
    qdrant_port: int = Field(default=6333, validation_alias="QDRANT_PORT")
    qdrant_prefer_grpc: bool = Field(
        default=True, validation_alias="QDRANT_PREFER_GRPC"
    )

    ollama_base_url: str = Field(
        default="http://localhost:11434", validation_alias="OLLAMA_BASE_URL"
    )
    embeddings_model: str = Field(
        default="nomic-embed-text", validation_alias="EMBEDDINGS_MODEL"
    )

    groq_api_key: Optional[str] = Field(default=None, validation_alias="GROQ_API_KEY")

    clerk_secret_key: Optional[str] = Field(
        default=None, validation_alias="CLERK_SECRET_KEY"
    )

    default_llm: LLMConfig = LLMConfig(
        provider="groq",
        model="meta-llama/llama-4-maverick-17b-128e-instruct",
        temperature=0.0,
    )

    conversation_llm: Optional[LLMConfig] = None
    ps1_llm: Optional[LLMConfig] = LLMConfig(
        provider="groq",
        model="llama-3.1-8b-instant",
        temperature=0.0,
    )
    ps2_llm: Optional[LLMConfig] = LLMConfig(
        provider="groq",
        model="llama-3.1-8b-instant",
        temperature=0.0,
    )
    retrieval_llm: Optional[LLMConfig] = LLMConfig(
        provider="groq",
        model="llama-3.1-8b-instant",
        temperature=0.0,
    )
    core_memory_llm: Optional[LLMConfig] = LLMConfig(
        provider="groq",
        model="llama-3.1-8b-instant",
        temperature=0.0,
    )
    recursive_summary_llm: Optional[LLMConfig] = LLMConfig(
        provider="groq",
        model="llama-3.1-8b-instant",
        temperature=0.0,
    )

    def _to_task_settings(self, cfg: Optional[LLMConfig]) -> Optional[LLMTaskSettings]:
        """Convert LLMConfig to LLMTaskSettings."""
        if cfg is None:
            return None
        return LLMTaskSettings(
            provider=cfg.provider,
            model=cfg.model,
            temperature=cfg.temperature,
            enable_thinking=False,
        )

    def to_memblocks_config(self) -> MemBlocksConfig:
        """Convert to MemBlocksConfig with llm_settings."""
        default_settings = LLMTaskSettings(
            provider=self.default_llm.provider,
            model=self.default_llm.model,
            temperature=self.default_llm.temperature,
            enable_thinking=False,
        )

        llm_settings = LLMSettings(
            default=default_settings,
            conversation=self._to_task_settings(self.conversation_llm),
            ps1_semantic_extraction=self._to_task_settings(self.ps1_llm),
            ps2_conflict_resolution=self._to_task_settings(self.ps2_llm),
            retrieval=self._to_task_settings(self.retrieval_llm),
            core_memory_extraction=self._to_task_settings(self.core_memory_llm),
            recursive_summary=self._to_task_settings(self.recursive_summary_llm),
        )

        ps1_temp = self.ps1_llm.temperature if self.ps1_llm else 0.0

        return MemBlocksConfig(
            llm_provider_name=self.default_llm.provider,
            llm_model=self.default_llm.model,
            llm_settings=llm_settings,
            llm_convo_temperature=self.default_llm.temperature,
            llm_semantic_extraction_temperature=ps1_temp,
            llm_core_extraction_temperature=0.0,
            llm_recursive_summary_gen_temperature=0.3,
            llm_memory_update_temperature=0.0,
            mongodb_connection_string=self.mongodb_connection_string,
            mongodb_database_name=self.mongodb_database_name,
            mongo_collection_users="users",
            mongo_collection_blocks="memory_blocks",
            mongo_collection_core_memories="core_memories",
            qdrant_host=self.qdrant_host,
            qdrant_port=self.qdrant_port,
            qdrant_prefer_grpc=self.qdrant_prefer_grpc,
            semantic_collection_template="{block_id}_semantic",
            resource_collection_template="{block_id}_resource",
            ollama_base_url=self.ollama_base_url,
            embeddings_model=self.embeddings_model,
            sparse_embeddings_model="prithivida/Splade_PP_en_v1",
            memory_window_limit=10,
            keep_last_n=4,
            retrieval_num_query_expansions=3,
            retrieval_num_hypothetical_paragraphs=2,
            retrieval_top_k_per_query=5,
            retrieval_final_top_k=10,
            retrieval_enable_query_expansion=True,
            retrieval_enable_hypothetical_paragraphs=True,
            retrieval_enable_reranking=True,
            retrieval_enable_sparse=True,
            groq_api_key=self.groq_api_key,
            gemini_api_key=None,
            openrouter_api_key=None,
            openrouter_fallback_models=None,
            openrouter_enable_thinking=False,
            cohere_api_key=None,
            arize_space_id=None,
            arize_api_key=None,
            arize_project_name="memBlocks",
            clerk_publishable_key=None,
            clerk_secret_key=self.clerk_secret_key,
        )


@lru_cache(maxsize=1)
def get_backend_config() -> BackendConfig:
    """Return (and cache) the BackendConfig instance."""
    return BackendConfig()


@lru_cache(maxsize=1)
def get_config() -> MemBlocksConfig:
    """Return (and cache) the MemBlocksConfig instance."""
    backend_config = get_backend_config()
    return backend_config.to_memblocks_config()


@lru_cache(maxsize=1)
def get_client() -> MemBlocksClient:
    """Return (and cache) the shared MemBlocksClient instance."""
    config = get_config()
    return MemBlocksClient(config)


__all__ = [
    "get_config",
    "get_client",
    "get_backend_config",
    "BackendConfig",
    "LLMConfig",
]
