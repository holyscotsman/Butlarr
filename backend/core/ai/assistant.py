"""AI Assistant for conversational chat about Plex library management."""

from typing import Dict, Any, List, Optional
import structlog

from backend.core.ai.provider import AIProvider

logger = structlog.get_logger(__name__)

ASSISTANT_SYSTEM_PROMPT = """You are Butlarr, an AI assistant specialized in Plex media library management. You help users with:

1. **Library Management**: Advice on organizing, tagging, and maintaining media libraries
2. **Recommendations**: Suggesting movies and TV shows based on user preferences
3. **Troubleshooting**: Helping diagnose and fix common Plex issues
4. **Storage**: Guidance on storage management, transcoding, and optimization
5. **Quality**: Explaining video/audio quality, codecs, and format differences
6. **Metadata**: Helping with metadata management, posters, and artwork
7. **Integration**: Advice on integrating with Radarr, Sonarr, Overseerr, and other *arr apps

Be helpful, concise, and friendly. Use technical terms when appropriate but explain them if needed.
If you don't know something specific about the user's setup, ask clarifying questions.

Keep responses focused and practical. Avoid overly long explanations unless the user asks for details."""


class AssistantChat:
    """AI Chat assistant for Butlarr."""

    def __init__(self, provider: AIProvider, config: Any):
        """Initialize the assistant.

        Args:
            provider: AIProvider instance for generating responses
            config: Application configuration
        """
        self.provider = provider
        self.config = config

    async def chat(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """Send a message and get a response.

        Args:
            message: The user's message
            conversation_history: Optional list of previous messages
                Each message should have 'role' and 'content' keys

        Returns:
            Dict with response, token usage, and cost information
        """
        # Build the full prompt with conversation history
        full_prompt = self._build_prompt(message, conversation_history or [])

        try:
            # Get preferred model from config
            model = getattr(self.config.ai, 'assistant_model', None)
            provider_name = getattr(self.config.ai, 'preferred_provider', None)

            result = await self.provider.generate(
                prompt=full_prompt,
                system_prompt=ASSISTANT_SYSTEM_PROMPT,
                model=model,
                provider=provider_name,
                max_tokens=2048,
                temperature=0.7,
            )

            return {
                "response": result["content"],
                "model": result["model"],
                "provider": result["provider"],
                "input_tokens": result["input_tokens"],
                "output_tokens": result["output_tokens"],
                "total_tokens": result["total_tokens"],
                "cost_usd": result["cost_usd"],
            }
        except Exception as e:
            logger.error("Assistant chat failed", error=str(e))
            raise

    def _build_prompt(
        self,
        message: str,
        history: List[Dict[str, str]]
    ) -> str:
        """Build the full prompt including conversation history.

        Args:
            message: Current user message
            history: List of previous messages

        Returns:
            Formatted prompt string
        """
        if not history:
            return message

        # Build conversation context
        parts = []
        for msg in history[-10:]:  # Keep last 10 messages for context
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                parts.append(f"User: {content}")
            elif role == "assistant":
                parts.append(f"Assistant: {content}")

        # Add current message
        parts.append(f"User: {message}")

        return "\n\n".join(parts)
