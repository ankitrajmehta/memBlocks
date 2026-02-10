"""Centralized LLM manager using LangChain."""

from typing import Optional
from config import settings
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate



class LLMManager:
    """Singleton manager for LLM instances and chains."""
    
    _instance: Optional['LLMManager'] = None
    _chat_llm: Optional[ChatGroq] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._chat_llm is None:
            self._initialize_llm()
    
    def _initialize_llm(self):
        """Initialize LangChain ChatGroq instance."""
        api_key = settings.groq_api_key
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        
        self._chat_llm = ChatGroq(
            model=settings.llm_model,
            temperature=settings.llm_convo_temperature,
            groq_api_key=api_key
        )
    
    @property
    def chat_llm(self) -> ChatGroq:
        """Get the chat LLM instance."""
        if self._chat_llm is None:
            self._initialize_llm()
        return self._chat_llm
    
    def get_chat_llm(self, temperature: Optional[float] = None) -> ChatGroq:
        """Get a chat LLM with custom temperature."""
        api_key = settings.groq_api_key
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        if temperature is None:
            temperature = settings.llm_convo_temperature
        return ChatGroq(
            model=settings.llm_model,
            temperature=temperature,
            groq_api_key=api_key
        )
    
    def create_structured_chain(self, system_prompt: str, pydantic_model, temperature: float = 0.0):
        """
        Create a LangChain structured output chain using Groq's native JSON mode.
        
        Args:
            system_prompt: System prompt for the LLM
            pydantic_model: Pydantic model for structured output
            temperature: Temperature for generation
            
        Returns:
            Runnable chain that outputs pydantic_model instances
        """
        # Get LLM instance
        llm = self.get_chat_llm(temperature=temperature)
        
        # Explicitly use json_schema method (not tool calling) for Groq's native structured output
        # include_raw=False means we only get the parsed Pydantic object back
        structured_llm = llm.with_structured_output(
            pydantic_model,
            method="json_schema",
            include_raw=False
        )
        
        # Create a simple prompt template without format_instructions
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "{input}")
        ])
        
        chain = prompt | structured_llm
        return chain


# Singleton instance
llm_manager = LLMManager()
