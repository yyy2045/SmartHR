"""
LLM 服务 - 多 LLM 提供商的统一接口
支持: DeepSeek, OpenAI, Anthropic
"""

import os
from typing import Optional, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from src.config import settings


class LLMService:
    """统一 LLM 服务，支持多提供商"""

    def __init__(self):
        self.provider = settings.llm_provider
        self._client = None

    def _get_client(self):
        """根据提供商获取或创建 LLM 客户端"""
        if self._client is not None:
            return self._client

        if self.provider == "deepseek":
            self._client = ChatOpenAI(
                api_key=settings.deepseek_api_key,
                base_url=settings.deepseek_base_url,
                model=settings.deepseek_model,
                temperature=0.7,
                request_timeout=120,
                max_retries=2
            )
        elif self.provider == "openai":
            self._client = ChatOpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
                model=settings.openai_model,
                temperature=0.7,
                request_timeout=120,
                max_retries=2
            )
        elif self.provider == "anthropic":
            try:
                from anthropic import Anthropic
                self._client = Anthropic(
                    api_key=settings.anthropic_api_key,
                )
            except ImportError:
                raise ImportError("请安装 anthropic 包: pip install anthropic")
        else:
            self._client = ChatOpenAI(
                api_key=settings.deepseek_api_key,
                base_url=settings.deepseek_base_url,
                model=settings.deepseek_model,
                temperature=0.7,
                request_timeout=120,
                max_retries=2
            )
        return self._client

    def chat(self, messages: list, temperature: float = 0.7) -> str:
        """向 LLM 发送聊天请求（同步）"""
        client = self._get_client()

        if self.provider == "anthropic":
            # Anthropic 使用不同的消息格式
            system_content = ""
            human_messages = []
            for msg in messages:
                if isinstance(msg, dict):
                    if msg.get("role") == "system":
                        system_content = msg.get("content", "")
                    else:
                        human_messages.append({
                            "role": msg.get("role", "user"),
                            "content": msg.get("content", "")
                        })
                else:
                    human_messages.append({"role": "user", "content": str(msg)})

            response = client.messages.create(
                model=settings.anthropic_model,
                max_tokens=4096,
                temperature=temperature,
                system=system_content if system_content else None,
                messages=human_messages
            )
            return response.content[0].text

        # LangChain ChatOpenAI 路径
        langchain_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                if msg.get("role") == "system":
                    langchain_messages.append(SystemMessage(content=msg["content"]))
                else:
                    langchain_messages.append(HumanMessage(content=str(msg)))
            else:
                langchain_messages.append(HumanMessage(content=str(msg)))

        response = client.invoke(langchain_messages)
        return response.content

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """简单的生成方法（同步）"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return self.chat(messages)


# 全局实例
llm_service = LLMService()