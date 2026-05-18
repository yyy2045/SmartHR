"""
LLM Service - Unified Interface for multiple LLM providers
Supports: DeepSeek, OpenAI, Anthropic
"""

import os
from typing import Optional, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from src.config import settings


class LLMService:
    """Unified LLM service supporting multiple providers"""

    def __init__(self):
        self.provider = settings.llm_provider
        self._client = None

    def _get_client(self) -> ChatOpenAI:
        """Get or create LLM client based on provider"""
        if self._client is not None:
            return self._client

        if self.provider == "deepseek":
            return ChatOpenAI(
                api_key=settings.deepseek_api_key,
                base_url=settings.deepseek_base_url,
                model=settings.deepseek_model,
                temperature=0.7
            )
        elif self.provider == "openai":
            return ChatOpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
                model=settings.openai_model,
                temperature=0.7
            )
        elif self.provider == "anthropic":
            return ChatOpenAI(
                api_key=settings.anthropic_api_key,
                base_url="https://api.anthropic.com",
                model=settings.anthropic_model,
                temperature=0.7
            )
        else:
            # Default to deepseek
            return ChatOpenAI(
                api_key=settings.deepseek_api_key,
                base_url=settings.deepseek_base_url,
                model=settings.deepseek_model,
                temperature=0.7
            )

    def chat(self, messages: list, temperature: float = 0.7) -> str:
        """Send chat request to LLM"""
        client = self._get_client()

        # Convert messages to LangChain format
        langchain_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                if msg.get("role") == "system":
                    langchain_messages.append(SystemMessage(content=msg["content"]))
                else:
                    langchain_messages.append(HumanMessage(content=msg["content"]))
            else:
                langchain_messages.append(HumanMessage(content=str(msg)))

        response = client.invoke(langchain_messages)
        return response.content

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Simple generate method"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return self.chat(messages)


# Global instance
llm_service = LLMService()