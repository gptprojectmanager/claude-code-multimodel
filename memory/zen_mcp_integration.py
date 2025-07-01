"""
Zen MCP Integration for Claude Code Multi-Model
==============================================

Integrates Zen MCP Server conversation memory and AI-to-AI orchestration
into the multi-provider LLM system.

Key Features:
- Cross-provider conversation memory
- AI-to-AI threading across different providers
- Session persistence during provider failover
- Context sharing between Vertex AI, GitHub Models, OpenRouter
"""

import asyncio
import uuid
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import sys
import os

# Add zen-mcp-server to path
sys.path.append('/home/sam/zen-mcp-server')

try:
    from utils.conversation_memory import ConversationMemory
    from utils.storage_backend import StorageBackend
    from providers.registry import ProviderRegistry
except ImportError as e:
    print(f"Warning: Zen MCP Server not available: {e}")
    ConversationMemory = None
    StorageBackend = None
    ProviderRegistry = None


@dataclass
class ProviderSession:
    """Session data for a specific provider"""
    provider_name: str
    model_name: str
    conversation_id: str
    created_at: datetime
    last_used: datetime
    token_usage: Dict[str, int]
    performance_metrics: Dict[str, float]


@dataclass
class CrossProviderMemory:
    """Memory state that persists across provider switches"""
    session_id: str
    user_context: str
    conversation_history: List[Dict[str, Any]]
    provider_sessions: Dict[str, ProviderSession]
    current_provider: str
    created_at: datetime
    last_updated: datetime


class ZenMCPOrchestrator:
    """
    Orchestrates AI-to-AI conversations across multiple providers
    using Zen MCP Server conversation memory system.
    """
    
    def __init__(self):
        self.memory = ConversationMemory() if ConversationMemory else None
        self.storage = StorageBackend() if StorageBackend else None
        self.provider_registry = ProviderRegistry() if ProviderRegistry else None
        self.active_sessions: Dict[str, CrossProviderMemory] = {}
        
    async def create_session(self, user_context: str = "") -> str:
        """Create a new cross-provider conversation session"""
        session_id = str(uuid.uuid4())
        
        memory = CrossProviderMemory(
            session_id=session_id,
            user_context=user_context,
            conversation_history=[],
            provider_sessions={},
            current_provider="vertex_claude",  # Default to primary
            created_at=datetime.now(),
            last_updated=datetime.now()
        )
        
        self.active_sessions[session_id] = memory
        
        # Initialize Zen MCP conversation if available
        if self.memory:
            zen_conversation_id = await self.memory.create_conversation_thread(
                initial_context=user_context,
                metadata={"session_id": session_id, "type": "multi_provider"}
            )
            memory.conversation_history.append({
                "type": "zen_thread_created",
                "zen_conversation_id": zen_conversation_id,
                "timestamp": datetime.now().isoformat()
            })
        
        return session_id
    
    async def switch_provider(self, session_id: str, new_provider: str, 
                            reason: str = "user_request") -> bool:
        """
        Switch conversation to a different provider while preserving context
        """
        if session_id not in self.active_sessions:
            return False
            
        memory = self.active_sessions[session_id]
        old_provider = memory.current_provider
        
        # Save current provider session state
        if old_provider not in memory.provider_sessions:
            memory.provider_sessions[old_provider] = ProviderSession(
                provider_name=old_provider,
                model_name="",  # Will be filled by actual implementation
                conversation_id=session_id,
                created_at=datetime.now(),
                last_used=datetime.now(),
                token_usage={},
                performance_metrics={}
            )
        
        # Update session
        memory.current_provider = new_provider
        memory.last_updated = datetime.now()
        
        # Log provider switch
        memory.conversation_history.append({
            "type": "provider_switch",
            "from_provider": old_provider,
            "to_provider": new_provider,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        })
        
        # If Zen MCP is available, continue conversation thread
        if self.memory:
            await self.memory.add_turn_to_conversation(
                conversation_id=session_id,
                tool_name="provider_switch",
                user_input=f"Switching from {old_provider} to {new_provider}: {reason}",
                assistant_response=f"Context preserved. Now using {new_provider}.",
                metadata={"provider_switch": True}
            )
        
        return True
    
    async def add_conversation_turn(self, session_id: str, provider: str,
                                 user_input: str, assistant_response: str,
                                 metadata: Optional[Dict] = None) -> bool:
        """Add a conversation turn with provider tracking"""
        if session_id not in self.active_sessions:
            return False
            
        memory = self.active_sessions[session_id]
        
        turn_data = {
            "type": "conversation_turn",
            "provider": provider,
            "user_input": user_input,
            "assistant_response": assistant_response,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        memory.conversation_history.append(turn_data)
        memory.last_updated = datetime.now()
        
        # Add to Zen MCP memory if available
        if self.memory:
            await self.memory.add_turn_to_conversation(
                conversation_id=session_id,
                tool_name=f"chat_{provider}",
                user_input=user_input,
                assistant_response=assistant_response,
                metadata={"provider": provider, **(metadata or {})}
            )
        
        return True
    
    def get_session_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get complete session context for provider handoff"""
        if session_id not in self.active_sessions:
            return None
            
        memory = self.active_sessions[session_id]
        
        # Build context summary
        context = {
            "session_id": session_id,
            "current_provider": memory.current_provider,
            "user_context": memory.user_context,
            "conversation_summary": self._summarize_conversation(memory),
            "provider_history": list(memory.provider_sessions.keys()),
            "total_turns": len([h for h in memory.conversation_history 
                              if h.get("type") == "conversation_turn"]),
            "session_duration": (datetime.now() - memory.created_at).total_seconds(),
            "last_updated": memory.last_updated.isoformat()
        }
        
        return context
    
    def _summarize_conversation(self, memory: CrossProviderMemory) -> str:
        """Create a summary of the conversation for context transfer"""
        conversation_turns = [h for h in memory.conversation_history 
                            if h.get("type") == "conversation_turn"]
        
        if not conversation_turns:
            return "No conversation history yet."
        
        # Get last few turns for context
        recent_turns = conversation_turns[-3:]  # Last 3 turns
        
        summary_parts = []
        for turn in recent_turns:
            provider = turn.get("provider", "unknown")
            user_input = turn.get("user_input", "")[:100]  # Truncate
            summary_parts.append(f"[{provider}] User: {user_input}...")
        
        return " | ".join(summary_parts)
    
    async def cleanup_session(self, session_id: str) -> bool:
        """Clean up session resources"""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            
            # Clean up Zen MCP resources if available
            if self.memory:
                await self.memory.cleanup_conversation(session_id)
            
            return True
        return False


# Global orchestrator instance
zen_orchestrator = ZenMCPOrchestrator()


async def init_zen_integration():
    """Initialize Zen MCP integration"""
    if not ConversationMemory:
        print("Warning: Zen MCP Server not available. Running without conversation memory.")
        return False
    
    print("✅ Zen MCP Integration initialized successfully")
    return True


def get_orchestrator() -> ZenMCPOrchestrator:
    """Get the global orchestrator instance"""
    return zen_orchestrator