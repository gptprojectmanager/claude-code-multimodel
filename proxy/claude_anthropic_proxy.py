#!/usr/bin/env python3
"""
Claude Anthropic API Proxy
Ispirato a https://github.com/CogAgent/claude-code-proxy
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn
import logging
import json
import os
import time
import uuid
from typing import List, Dict, Any, Optional, Union, Literal
from pydantic import BaseModel, Field, field_validator
import litellm
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configure LiteLLM
litellm.drop_params = True
logger.info("✅ Enabled LiteLLM drop_params=True")

app = FastAPI(title="Claude Anthropic API Proxy", version="1.0.0")

# Environment Configuration
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

# Google Cloud / Vertex AI
GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT")
GOOGLE_CLOUD_LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

# Configuration
PREFERRED_PROVIDER = os.environ.get("PREFERRED_PROVIDER", "openrouter").lower()
BIG_MODEL = os.environ.get("BIG_MODEL", "openai/gpt-4o")
SMALL_MODEL = os.environ.get("SMALL_MODEL", "openai/gpt-4o-mini")

logger.info(f"🔧 Preferred provider: {PREFERRED_PROVIDER}")
logger.info(f"🔧 Big model: {BIG_MODEL}")
logger.info(f"🔧 Small model: {SMALL_MODEL}")

# Model Lists
OPENROUTER_MODELS = {
    "claude-3-5-sonnet": "openrouter/anthropic/claude-3.5-sonnet",
    "claude-3-5-haiku": "openrouter/anthropic/claude-3.5-haiku",
    "gpt-4o": "openrouter/openai/gpt-4o",
    "gpt-4o-mini": "openrouter/openai/gpt-4o-mini"
}

GITHUB_MODELS = {
    "gpt-4o": "github/gpt-4o",
    "gpt-4o-mini": "github/gpt-4o-mini"
}

VERTEX_MODELS = {
    "claude-3-5-sonnet": "vertex_ai/claude-3-5-sonnet@20241022",
    "claude-3-5-haiku": "vertex_ai/claude-3-5-haiku@20241022",
    "gemini-1.5-pro": "vertex_ai/gemini-1.5-pro",
    "gemini-1.5-flash": "vertex_ai/gemini-1.5-flash"
}

# Pydantic Models
class TextContent(BaseModel):
    type: Literal["text"] = "text"
    text: str

class ImageContent(BaseModel):
    type: Literal["image"] = "image"
    source: Dict[str, Any]

class ToolUse(BaseModel):
    type: Literal["tool_use"] = "tool_use"
    id: str
    name: str
    input: Dict[str, Any]

class ToolResult(BaseModel):
    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str
    content: Union[str, List[Dict[str, Any]]]
    is_error: Optional[bool] = False

ContentBlock = Union[TextContent, ImageContent, ToolUse, ToolResult]

class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: Union[str, List[ContentBlock]]

class Tool(BaseModel):
    name: str
    description: str
    input_schema: Dict[str, Any]

class MessagesRequest(BaseModel):
    model: str
    messages: List[Message]
    system: Optional[Union[str, List[Dict[str, Any]]]] = None
    max_tokens: int = Field(default=4096, ge=1)
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    tools: Optional[List[Tool]] = None
    stream: Optional[bool] = False
    
    @field_validator('max_tokens')
    def validate_max_tokens(cls, v):
        """Limit max_tokens to reasonable values"""
        if v > 8192:
            logger.info(f"⚠️ Limiting max_tokens from {v} to 8192")
            return 8192
        return v
    
    @field_validator('model')
    def validate_and_map_model(cls, v):
        """Map Claude model names to appropriate providers"""
        original_model = v
        
        # Remove provider prefixes
        clean_model = v
        for prefix in ['anthropic/', 'claude/', 'openai/', 'openrouter/', 'github/', 'vertex_ai/']:
            if clean_model.startswith(prefix):
                clean_model = clean_model[len(prefix):]
                break
        
        # Model mapping logic
        mapped_model = None
        
        # Map Haiku (small/fast models)
        if 'haiku' in clean_model.lower() or 'small' in clean_model.lower():
            if PREFERRED_PROVIDER == "openrouter" and OPENROUTER_API_KEY:
                mapped_model = OPENROUTER_MODELS.get("claude-3-5-haiku", SMALL_MODEL)
            elif PREFERRED_PROVIDER == "github" and GITHUB_TOKEN:
                mapped_model = GITHUB_MODELS.get("gpt-4o-mini", "github/gpt-4o-mini")
            elif PREFERRED_PROVIDER == "vertex" and GOOGLE_CLOUD_PROJECT:
                mapped_model = VERTEX_MODELS.get("claude-3-5-haiku", "vertex_ai/claude-3-5-haiku@20241022")
            else:
                mapped_model = SMALL_MODEL
        
        # Map Sonnet (large/smart models)
        elif 'sonnet' in clean_model.lower() or 'large' in clean_model.lower():
            if PREFERRED_PROVIDER == "openrouter" and OPENROUTER_API_KEY:
                mapped_model = OPENROUTER_MODELS.get("claude-3-5-sonnet", BIG_MODEL)
            elif PREFERRED_PROVIDER == "github" and GITHUB_TOKEN:
                mapped_model = GITHUB_MODELS.get("gpt-4o", "github/gpt-4o")
            elif PREFERRED_PROVIDER == "vertex" and GOOGLE_CLOUD_PROJECT:
                mapped_model = VERTEX_MODELS.get("claude-3-5-sonnet", "vertex_ai/claude-3-5-sonnet@20241022")
            else:
                mapped_model = BIG_MODEL
        
        # Direct model name mapping
        else:
            # Try to find direct mapping
            if PREFERRED_PROVIDER == "openrouter" and clean_model in OPENROUTER_MODELS:
                mapped_model = OPENROUTER_MODELS[clean_model]
            elif PREFERRED_PROVIDER == "github" and clean_model in GITHUB_MODELS:
                mapped_model = GITHUB_MODELS[clean_model]
            elif PREFERRED_PROVIDER == "vertex" and clean_model in VERTEX_MODELS:
                mapped_model = VERTEX_MODELS[clean_model]
            else:
                # Default fallback
                mapped_model = BIG_MODEL if 'gpt-4' in clean_model else SMALL_MODEL
        
        if mapped_model and mapped_model != original_model:
            provider = mapped_model.split('/')[0] if '/' in mapped_model else 'unknown'
            emoji = {"openrouter": "🔄", "github": "🐙", "vertex_ai": "🔵", "openai": "🟢"}.get(provider, "📍")
            logger.info(f"{emoji} MODEL MAPPING: '{original_model}' ➡️ '{mapped_model}'")
        
        return mapped_model or original_model

def convert_anthropic_to_litellm(request: MessagesRequest) -> Dict[str, Any]:
    """Convert Anthropic format to LiteLLM/OpenAI format"""
    litellm_request = {
        "model": request.model,
        "messages": [],
        "max_tokens": request.max_tokens,
        "stream": request.stream
    }
    
    if request.temperature is not None:
        litellm_request["temperature"] = request.temperature
    if request.top_p is not None:
        litellm_request["top_p"] = request.top_p
    
    # Add system message
    if request.system:
        if isinstance(request.system, str):
            litellm_request["messages"].append({"role": "system", "content": request.system})
        elif isinstance(request.system, list):
            system_text = ""
            for block in request.system:
                if isinstance(block, dict) and block.get("type") == "text":
                    system_text += block.get("text", "") + "\n\n"
            if system_text:
                litellm_request["messages"].append({"role": "system", "content": system_text.strip()})
    
    # Convert messages
    for msg in request.messages:
        if isinstance(msg.content, str):
            litellm_request["messages"].append({"role": msg.role, "content": msg.content})
        else:
            # Handle complex content
            processed_content = []
            tool_calls = []
            
            for block in msg.content:
                if isinstance(block, dict):
                    block_type = block.get("type")
                    if block_type == "text":
                        processed_content.append({"type": "text", "text": block.get("text", "")})
                    elif block_type == "tool_use" and msg.role == "assistant":
                        tool_calls.append({
                            "id": block.get("id"),
                            "type": "function",
                            "function": {
                                "name": block.get("name"),
                                "arguments": json.dumps(block.get("input", {}))
                            }
                        })
                    elif block_type == "tool_result" and msg.role == "user":
                        # Convert tool result to text
                        tool_id = block.get("tool_use_id", "unknown")
                        content = block.get("content", "")
                        if isinstance(content, list):
                            content = json.dumps(content)
                        processed_content.append({
                            "type": "text", 
                            "text": f"Tool result for {tool_id}: {content}"
                        })
                elif hasattr(block, 'type'):
                    if block.type == "text":
                        processed_content.append({"type": "text", "text": block.text})
                    elif block.type == "tool_use" and msg.role == "assistant":
                        tool_calls.append({
                            "id": block.id,
                            "type": "function",
                            "function": {
                                "name": block.name,
                                "arguments": json.dumps(block.input)
                            }
                        })
            
            message = {"role": msg.role}
            if processed_content:
                if len(processed_content) == 1 and processed_content[0]["type"] == "text":
                    message["content"] = processed_content[0]["text"]
                else:
                    message["content"] = processed_content
            else:
                message["content"] = None
                
            if tool_calls:
                message["tool_calls"] = tool_calls
                
            litellm_request["messages"].append(message)
    
    # Add tools
    if request.tools:
        litellm_request["tools"] = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.input_schema
                }
            }
            for tool in request.tools
        ]
    
    # Set API key based on model
    model = request.model
    if model.startswith("openrouter/"):
        litellm_request["api_key"] = OPENROUTER_API_KEY
        litellm_request["api_base"] = "https://openrouter.ai/api/v1"
    elif model.startswith("github/"):
        litellm_request["api_key"] = GITHUB_TOKEN
    elif model.startswith("vertex_ai/"):
        litellm_request["vertex_project"] = GOOGLE_CLOUD_PROJECT
        litellm_request["vertex_location"] = GOOGLE_CLOUD_LOCATION
    else:
        litellm_request["api_key"] = OPENAI_API_KEY
    
    return litellm_request

def convert_litellm_to_anthropic(response: Dict[str, Any]) -> Dict[str, Any]:
    """Convert LiteLLM response to Anthropic format"""
    if "choices" not in response:
        return response
    
    choice = response["choices"][0]
    message = choice.get("message", {})
    
    # Build content blocks
    content = []
    
    # Add text content
    if message.get("content"):
        content.append({
            "type": "text",
            "text": message["content"]
        })
    
    # Add tool calls
    if message.get("tool_calls"):
        for tool_call in message["tool_calls"]:
            function = tool_call.get("function", {})
            content.append({
                "type": "tool_use",
                "id": tool_call.get("id"),
                "name": function.get("name"),
                "input": json.loads(function.get("arguments", "{}"))
            })
    
    # Build Anthropic response
    anthropic_response = {
        "id": f"msg_{uuid.uuid4().hex[:24]}",
        "type": "message",
        "role": "assistant",
        "content": content,
        "model": response.get("model", "unknown"),
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {
            "input_tokens": response.get("usage", {}).get("prompt_tokens", 0),
            "output_tokens": response.get("usage", {}).get("completion_tokens", 0)
        }
    }
    
    return anthropic_response

@app.post("/v1/messages")
async def create_message(request: MessagesRequest):
    """Create a message using the Anthropic API format"""
    try:
        start_time = time.time()
        
        # Convert to LiteLLM format
        litellm_request = convert_anthropic_to_litellm(request)
        
        logger.info(f"🚀 Request: {request.model} | Messages: {len(request.messages)} | Stream: {request.stream}")
        
        if request.stream:
            # Handle streaming
            async def generate():
                try:
                    stream = await litellm.acompletion(**litellm_request)
                    
                    # Send initial event
                    yield f"data: {json.dumps({'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'text', 'text': ''}})}\n\n"
                    
                    full_text = ""
                    async for chunk in stream:
                        if chunk.choices and chunk.choices[0].delta.content:
                            content = chunk.choices[0].delta.content
                            full_text += content
                            
                            event_data = {
                                "type": "content_block_delta",
                                "index": 0,
                                "delta": {"type": "text_delta", "text": content}
                            }
                            yield f"data: {json.dumps(event_data)}\n\n"
                    
                    # Send final events
                    yield f"data: {json.dumps({'type': 'content_block_stop', 'index': 0})}\n\n"
                    yield f"data: {json.dumps({'type': 'message_stop'})}\n\n"
                    
                except Exception as e:
                    logger.error(f"❌ Streaming error: {e}")
                    error_event = {
                        "type": "error",
                        "error": {"type": "api_error", "message": str(e)}
                    }
                    yield f"data: {json.dumps(error_event)}\n\n"
            
            return StreamingResponse(generate(), media_type="text/event-stream")
        
        else:
            # Handle non-streaming
            response = await litellm.acompletion(**litellm_request)
            anthropic_response = convert_litellm_to_anthropic(response.model_dump())
            
            duration = time.time() - start_time
            logger.info(f"✅ Response: {anthropic_response['usage']['output_tokens']} tokens | {duration:.2f}s")
            
            return anthropic_response
    
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": time.time()}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Claude Anthropic API Proxy",
        "version": "1.0.0",
        "preferred_provider": PREFERRED_PROVIDER,
        "endpoints": ["/v1/messages", "/health"]
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)