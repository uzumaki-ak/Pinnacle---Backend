import httpx
from typing import Optional, List, Dict, Any, AsyncIterator
from loguru import logger
import google.generativeai as genai
from openai import AsyncOpenAI
import os

from app.config import settings, LLM_CONFIG

class LLMService:
    """Multi-provider LLM service with automatic fallback"""
    
    def __init__(self):
        self.providers = settings.LLM_PROVIDERS
        self.current_provider_idx = 0
        self._clients = {}
        self._init_clients()
    
    def _init_clients(self):
        """Initialize API clients for each provider"""
        # Groq (OpenAI-compatible)
        if settings.GROQ_API_KEY:
            self._clients["groq"] = AsyncOpenAI(
                api_key=settings.GROQ_API_KEY,
                base_url=LLM_CONFIG["groq"]["base_url"]
            )
        
        # Google Gemini
        if settings.GOOGLE_API_KEY:
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            self._clients["google"] = genai
        
        # Euron (OpenAI-compatible)
        if settings.EURON_API_KEY:
            self._clients["euron"] = AsyncOpenAI(
                api_key=settings.EURON_API_KEY,
                base_url=LLM_CONFIG["euron"]["base_url"]
            )
        
        # OpenRouter (OpenAI-compatible)
        if settings.OPENROUTER_API_KEY:
            self._clients["openrouter"] = AsyncOpenAI(
                api_key=settings.OPENROUTER_API_KEY,
                base_url=LLM_CONFIG["openrouter"]["base_url"]
            )
        
        # Mistral (OpenAI-compatible)
        if settings.MISTRAL_API_KEY:
            self._clients["mistral"] = AsyncOpenAI(
                api_key=settings.MISTRAL_API_KEY,
                base_url=LLM_CONFIG["mistral"]["base_url"]
            )
        
        logger.info(f"Initialized {len(self._clients)} LLM providers: {list(self._clients.keys())}")
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        stream: bool = False,
        user_api_keys: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Get chat completion with automatic fallback across providers
        
        Args:
            messages: List of chat messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            stream: Whether to stream response
            user_api_keys: Optional user-provided API keys
        
        Returns:
            Response dict with content and metadata
        """
        errors = []
        
        # Try each provider in order
        for provider in self.providers:
            try:
                logger.info(f"Attempting LLM request with provider: {provider}")
                
                # Use user's API key if provided
                if user_api_keys and provider in user_api_keys:
                    response = await self._call_provider_with_key(
                        provider, messages, temperature, max_tokens, 
                        stream, user_api_keys[provider]
                    )
                elif provider in self._clients:
                    response = await self._call_provider(
                        provider, messages, temperature, max_tokens, stream
                    )
                else:
                    logger.warning(f"Provider {provider} not configured, skipping")
                    continue
                
                logger.success(f"✅ LLM request successful with {provider}")
                return {
                    "content": response,
                    "provider": provider,
                    "model": settings.LLM_DEFAULT_MODEL[provider]
                }
                
            except Exception as e:
                error_msg = f"Provider {provider} failed: {str(e)}"
                logger.warning(error_msg)
                errors.append(error_msg)
                continue
        
        # All providers failed
        error_summary = " | ".join(errors)
        logger.error(f"❌ All LLM providers failed: {error_summary}")
        raise Exception(f"All LLM providers failed. Errors: {error_summary}")
    
    async def _call_provider(
        self,
        provider: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        stream: bool
    ) -> str:
        """Call specific provider"""
        
        if provider == "google":
            return await self._call_google(messages, temperature, max_tokens)
        
        # OpenAI-compatible providers (groq, euron, openrouter, mistral)
        client = self._clients[provider]
        model = settings.LLM_DEFAULT_MODEL[provider]
        
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream
        )
        
        if stream:
            return response  # Return stream object
        
        return response.choices[0].message.content
    
    async def _call_provider_with_key(
        self,
        provider: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        stream: bool,
        api_key: str
    ) -> str:
        """Call provider with user-provided API key"""
        
        if provider == "google":
            genai.configure(api_key=api_key)
            return await self._call_google(messages, temperature, max_tokens)
        
        # Create temporary client with user's key
        client = AsyncOpenAI(
            api_key=api_key,
            base_url=LLM_CONFIG[provider]["base_url"]
        )
        
        model = settings.LLM_DEFAULT_MODEL[provider]
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream
        )
        
        if stream:
            return response
        
        return response.choices[0].message.content
    
    async def _call_google(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int
    ) -> str:
        """Call Google Gemini API"""
        model = genai.GenerativeModel(settings.LLM_DEFAULT_MODEL["google"])
        
        # Convert messages to Gemini format
        prompt_parts = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            prompt_parts.append({"role": role, "parts": [msg["content"]]})
        
        response = await model.generate_content_async(
            prompt_parts,
            generation_config=genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens
            )
        )
        
        return response.text
    
    async def generate_tags(self, title: str, content: str, url: str) -> List[str]:
        """Generate relevant tags for content using LLM"""
        prompt = f"""Analyze this content and generate 3-7 relevant tags.
Return ONLY a comma-separated list of tags, no other text.

Title: {title}
URL: {url}
Content: {content[:500]}...

Tags:"""
        
        try:
            response = await self.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=50
            )
            
            tags_str = response["content"].strip()
            tags = [t.strip() for t in tags_str.split(",") if t.strip()]
            return tags[:7]  # Max 7 tags
            
        except Exception as e:
            logger.error(f"Auto-tagging failed: {e}")
            return []
    
    async def generate_summary(self, content: str, max_length: int = 200) -> str:
        """Generate a brief summary of content"""
        prompt = f"""Summarize this content in {max_length} characters or less:

{content[:2000]}

Summary:"""
        
        try:
            response = await self.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=100
            )
            return response["content"].strip()
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return content[:max_length]

# Global instance
llm_service = LLMService()