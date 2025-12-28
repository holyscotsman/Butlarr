"""AI assistant chat endpoints."""

from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db
from backend.db.models import Activity, ActionType, AIUsage
from backend.utils.config import get_config
from backend.core.ai.provider import AIProvider
from backend.core.ai.assistant import AssistantChat

router = APIRouter()


class ChatMessage(BaseModel):
    """Chat message."""
    role: str  # user or assistant
    content: str
    timestamp: Optional[datetime] = None


class ChatRequest(BaseModel):
    """Chat request."""
    message: str
    conversation_history: Optional[List[ChatMessage]] = None


class ChatResponse(BaseModel):
    """Chat response."""
    response: str
    tokens_used: int
    cost_usd: float
    model_used: str


@router.post("/chat", response_model=ChatResponse)
async def chat_with_assistant(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """Chat with the AI assistant."""
    config = get_config()

    if not config.ai.enabled or not config.ai.assistant_enabled:
        raise HTTPException(status_code=400, detail="AI assistant is disabled")

    # Initialize AI provider
    provider = AIProvider(
        anthropic_api_key=config.ai.anthropic_api_key,
        openai_api_key=config.ai.openai_api_key,
        ollama_url=config.ai.ollama_url,
    )

    # Check if any provider is available
    available = provider.get_available_providers()
    if not available:
        raise HTTPException(
            status_code=400,
            detail="No AI provider configured. Add an Anthropic or OpenAI API key in Settings, or wait for the embedded AI model to download."
        )

    # Create assistant
    assistant = AssistantChat(provider, config)

    # Build conversation history
    history = []
    if request.conversation_history:
        history = [
            {"role": msg.role, "content": msg.content}
            for msg in request.conversation_history
        ]

    try:
        result = await assistant.chat(request.message, history)

        # Log AI usage
        usage = AIUsage(
            provider=result["provider"],
            model=result["model"],
            input_tokens=result["input_tokens"],
            output_tokens=result["output_tokens"],
            total_tokens=result["total_tokens"],
            cost_usd=result["cost_usd"],
            purpose="assistant",
        )
        db.add(usage)

        activity = Activity(
            action_type=ActionType.AI_QUERY,
            title="AI Assistant Query",
            description=request.message[:100] + "..." if len(request.message) > 100 else request.message,
        )
        db.add(activity)
        await db.commit()

        return ChatResponse(
            response=result["response"],
            tokens_used=result["total_tokens"],
            cost_usd=result["cost_usd"],
            model_used=result["model"],
        )
    except ValueError as e:
        # Provider-related errors
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI chat failed: {str(e)}")


@router.get("/status")
async def get_ai_status():
    """Get AI service status."""
    config = get_config()
    return {
        "enabled": config.ai.enabled,
        "assistant_enabled": config.ai.assistant_enabled,
        "curator_enabled": config.ai.curator_enabled,
        "providers": {
            "anthropic": config.ai.has_anthropic,
            "openai": config.ai.has_openai,
            "ollama": bool(config.ai.ollama_url),
        },
    }


@router.get("/usage")
async def get_ai_usage(days: int = 30, db: AsyncSession = Depends(get_db)):
    """Get AI usage statistics."""
    from sqlalchemy import func, select
    from datetime import timedelta
    
    cutoff = datetime.utcnow() - timedelta(days=days)
    total_result = await db.execute(
        select(
            func.sum(AIUsage.total_tokens).label("tokens"),
            func.sum(AIUsage.cost_usd).label("cost"),
            func.count(AIUsage.id).label("requests"),
        ).where(AIUsage.created_at >= cutoff)
    )
    total = total_result.first()
    config = get_config()
    
    return {
        "period_days": days,
        "total_tokens": total.tokens or 0,
        "total_cost_usd": total.cost or 0,
        "total_requests": total.requests or 0,
        "budget": {
            "monthly_limit": config.ai.monthly_budget_limit,
            "remaining": max(0, config.ai.monthly_budget_limit - (total.cost or 0)),
        },
    }
