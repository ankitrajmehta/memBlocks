"""
Utilities for managing resources in background threads.
Helps bypass singleton constraints and creates thread-local instances.
"""

from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
from langchain_groq import ChatGroq
from config import settings
from llm.llm_manager import LLMManager

class BackgroundMongoDBManager:
    """Independent MongoDB manager for background threads."""
    
    def __init__(self):
        self._client: Optional[AsyncIOMotorClient] = None
        self._db = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize a fresh MongoDB async client."""
        connection_string = settings.mongodb_connection_string
        if not connection_string:
            raise ValueError("MONGODB_CONNECTION_STRING not found in environment variables")

        # Create a NEW client instance, bypassing the singleton logic of the main manager
        self._client = AsyncIOMotorClient(connection_string)
        self._db = self._client.memblocks
        
        # Collections
        self.users = self._db.users
        self.blocks = self._db.blocks
        self.core_memories = self._db.core_memories

    async def save_block(self, block_data: dict) -> str:
        """Save block using background connection."""
        from datetime import datetime
        block_data["meta_data"]["updated_at"] = datetime.utcnow().isoformat()
        
        block_id = block_data["meta_data"]["id"]
        await self.blocks.replace_one(
            {"meta_data.id": block_id},
            block_data,
            upsert=True
        )
        return block_id

    async def save_core_memory(self, block_id: str, persona_content: str, human_content: str) -> str:
        """Save core memory using background connection."""
        from datetime import datetime
        core_memory_doc = {
            "block_id": block_id,
            "persona_content": persona_content,
            "human_content": human_content,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = await self.core_memories.replace_one(
            {"block_id": block_id},
            core_memory_doc,
            upsert=True
        )
        
        if result.upserted_id:
            return str(result.upserted_id)
        else:
            doc = await self.core_memories.find_one({"block_id": block_id})
            return str(doc["_id"])

    async def get_core_memory(self, block_id: str):
        """Get core memory using background connection."""
        return await self.core_memories.find_one({"block_id": block_id})

    async def close(self):
        """Close the background client."""
        if self._client:
            self._client.close()


class BackgroundLLMProvider:
    """Wrapper to provide LLM capabilities in background."""
    
    def __init__(self):
        self._chat_llm = self._create_llm()
        
    def _create_llm(self) -> ChatGroq:
        """Create a fresh ChatGroq instance."""
        api_key = settings.groq_api_key
        if not api_key:
            raise ValueError("GROQ_API_KEY not found")
        
        return ChatGroq(
            model=settings.llm_model,
            temperature=settings.llm_convo_temperature,
            groq_api_key=api_key
        )
    
    @property
    def chat_llm(self) -> ChatGroq:
        return self._chat_llm
        
    def get_chat_llm(self, temperature: Optional[float] = None) -> ChatGroq:
        """Get new instance with specific temperature."""
        if temperature is None:
            return self._chat_llm
            
        return ChatGroq(
            model=settings.llm_model,
            temperature=temperature,
            groq_api_key=settings.groq_api_key
        )

    def create_structured_chain(self, system_prompt: str, pydantic_model, temperature: float = 0.0):
        """Re-implement create_structured_chain using the background LLM."""
        # This logic mirrors llm_manager.py but uses local self.get_chat_llm
        from langchain_core.prompts import ChatPromptTemplate
        
        llm = self.get_chat_llm(temperature=temperature)
        
        structured_llm = llm.with_structured_output(
            pydantic_model,
            method="json_schema",
            include_raw=False
        )
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "{input}")
        ])
        
        return prompt | structured_llm
