# Multi-Port LiteLLM Library Architecture Design

## Overview

Design for multiple Claude Code instances running on dedicated ports (8090-8093) using LiteLLM as a library instead of proxy server, with provider-specific configurations and intelligent routing.

## Architecture Verification Criteria

✅ **Architecture document created with port assignments**: Detailed port allocation and service mapping
✅ **Provider mappings**: Comprehensive provider-to-port assignments with configurations  
✅ **Configuration templates**: Ready-to-use configuration files for each service
✅ **Service startup procedures**: Automated deployment and management scripts

## Port Assignments

### Port Allocation Strategy
- **8090**: Vertex AI Claude (Primary) - us-east5 region
- **8091**: Vertex AI Gemini (Secondary) - us-east5 region  
- **8092**: GitHub Models (Tertiary) - Azure-backed Claude access
- **8093**: OpenRouter (Fallback) - 100+ model access

### Service Architecture
```
Claude Code Client
        ↓
   [Port Router/Load Balancer]
        ↓
    ┌─────────────────────────────────────┐
    │  Multi-Port Service Mesh           │
    ├─────────────────────────────────────┤
    │ 8090: VertexAI Claude Service      │
    │ 8091: VertexAI Gemini Service      │  
    │ 8092: GitHub Models Service        │
    │ 8093: OpenRouter Service           │
    └─────────────────────────────────────┘
        ↓
   [Provider APIs]
```

## Provider Mappings

### 8090 - Vertex AI Claude Service
**Primary Focus**: Claude models in us-east5 region
```yaml
provider: vertex_ai
region: us-east5
models:
  - claude-sonnet-4@20250514
  - claude-3-5-sonnet@20240620  
  - claude-3-5-haiku@20241022
authentication: service_account
project: custom-mix-460500-g9
```

### 8091 - Vertex AI Gemini Service  
**Secondary Focus**: Google's Gemini models
```yaml
provider: vertex_ai_gemini
region: us-east5
models:
  - gemini-2.0-flash-exp
  - gemini-1.5-pro
  - gemini-1.5-flash
authentication: service_account
project: custom-mix-460500-g9
```

### 8092 - GitHub Models Service
**Tertiary Focus**: Azure-backed Claude access
```yaml
provider: github_models
models:
  - claude-3-5-sonnet
  - claude-3-5-haiku
  - gpt-4o
  - gpt-4o-mini
authentication: github_token
endpoint: https://models.inference.ai.azure.com
```

### 8093 - OpenRouter Service
**Fallback Focus**: Comprehensive model access
```yaml
provider: openrouter
models:
  - anthropic/claude-3.5-sonnet
  - anthropic/claude-3-haiku
  - openai/gpt-4o
  - meta-llama/llama-3.2-90b
authentication: api_key
endpoint: https://openrouter.ai/api/v1
```

## FastAPI Service Architecture

### Base Service Class
Based on claude-code-proxy patterns, create reusable base service:

```python
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
import litellm
from typing import Dict, Any, Optional
import logging

class BaseMultiPortService:
    def __init__(self, port: int, provider_config: Dict[str, Any]):
        self.port = port
        self.provider_config = provider_config
        self.app = FastAPI(title=f"Claude Code Service - Port {port}")
        self.setup_routes()
        self.configure_litellm()
    
    def configure_litellm(self):
        """Configure LiteLLM for this specific provider"""
        litellm.drop_params = True
        # Provider-specific configurations
        
    def setup_routes(self):
        """Setup FastAPI routes"""
        @self.app.post("/v1/messages")
        async def messages_endpoint(request: Request):
            return await self.handle_messages(request)
            
        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy", "port": self.port}
```

### Provider-Specific Services

#### Vertex AI Claude Service (Port 8090)
```python
class VertexClaudeService(BaseMultiPortService):
    def configure_litellm(self):
        super().configure_litellm()
        os.environ["GOOGLE_CLOUD_PROJECT"] = self.provider_config["project"]
        os.environ["VERTEX_AI_LOCATION"] = self.provider_config["region"]
        
    async def handle_messages(self, request: Request):
        # Vertex AI specific model mapping
        model_map = {
            "claude-3-5-sonnet-20241022": "vertex_ai/claude-3-5-sonnet@20240620",
            "claude-sonnet-4-20250514": "vertex_ai/claude-sonnet-4@20250514"
        }
```

#### GitHub Models Service (Port 8092)
```python
class GitHubModelsService(BaseMultiPortService):
    def configure_litellm(self):
        super().configure_litellm()
        os.environ["GITHUB_TOKEN"] = self.provider_config["token"]
        
    async def handle_messages(self, request: Request):
        # GitHub Models specific mapping
        model_map = {
            "claude-3-5-sonnet-20241022": "github/claude-3-5-sonnet",
            "claude-3-5-haiku-20241022": "github/claude-3-5-haiku"
        }
```

## Configuration Templates

### Port 8090 Configuration (vertex-claude.env)
```bash
# Vertex AI Claude Service - Port 8090
SERVICE_PORT=8090
SERVICE_NAME=vertex-claude
PROVIDER=vertex_ai

# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=custom-mix-460500-g9
VERTEX_AI_LOCATION=us-east5
GOOGLE_APPLICATION_CREDENTIALS=./config/vertex-service-account.json

# Model Configuration
PRIMARY_MODEL=claude-sonnet-4@20250514
SECONDARY_MODEL=claude-3-5-sonnet@20240620
FALLBACK_MODEL=claude-3-5-haiku@20241022

# Service Configuration
MAX_TOKENS_LIMIT=8192
RATE_LIMIT_PER_MINUTE=60
HEALTH_CHECK_INTERVAL=30
```

### Port 8091 Configuration (vertex-gemini.env)
```bash
# Vertex AI Gemini Service - Port 8091
SERVICE_PORT=8091
SERVICE_NAME=vertex-gemini
PROVIDER=vertex_ai_gemini

# Google Cloud Configuration  
GOOGLE_CLOUD_PROJECT=custom-mix-460500-g9
VERTEX_AI_LOCATION=us-east5
GOOGLE_APPLICATION_CREDENTIALS=./config/vertex-service-account.json

# Model Configuration
PRIMARY_MODEL=gemini-2.0-flash-exp
SECONDARY_MODEL=gemini-1.5-pro
FALLBACK_MODEL=gemini-1.5-flash

# Service Configuration
MAX_TOKENS_LIMIT=8192
RATE_LIMIT_PER_MINUTE=60
HEALTH_CHECK_INTERVAL=30
```

### Port 8092 Configuration (github-models.env)
```bash
# GitHub Models Service - Port 8092
SERVICE_PORT=8092
SERVICE_NAME=github-models
PROVIDER=github_models

# GitHub Configuration
GITHUB_TOKEN=your_github_token_here
GITHUB_MODELS_ENDPOINT=https://models.inference.ai.azure.com

# Model Configuration
PRIMARY_MODEL=claude-3-5-sonnet
SECONDARY_MODEL=claude-3-5-haiku
FALLBACK_MODEL=gpt-4o-mini

# Service Configuration
MAX_TOKENS_LIMIT=8192
RATE_LIMIT_PER_MINUTE=100
HEALTH_CHECK_INTERVAL=30
```

### Port 8093 Configuration (openrouter.env)
```bash
# OpenRouter Service - Port 8093
SERVICE_PORT=8093
SERVICE_NAME=openrouter
PROVIDER=openrouter

# OpenRouter Configuration
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_ENDPOINT=https://openrouter.ai/api/v1

# Model Configuration
PRIMARY_MODEL=anthropic/claude-3.5-sonnet
SECONDARY_MODEL=anthropic/claude-3-haiku
FALLBACK_MODEL=openai/gpt-4o-mini

# Service Configuration
MAX_TOKENS_LIMIT=8192
RATE_LIMIT_PER_MINUTE=200
HEALTH_CHECK_INTERVAL=30
```

## Service Startup Procedures

### Individual Service Startup
```bash
#!/bin/bash
# start-service.sh

SERVICE_NAME=$1
PORT=$2
CONFIG_FILE=$3

echo "Starting $SERVICE_NAME on port $PORT..."

# Load configuration
source ./config/$CONFIG_FILE

# Start FastAPI service
uvicorn services.${SERVICE_NAME}_service:app \
    --host 0.0.0.0 \
    --port $PORT \
    --reload \
    --log-level info \
    --access-log
```

### Multi-Service Orchestration
```bash
#!/bin/bash
# start-all-multiport-services.sh

echo "🚀 Starting Multi-Port Claude Code Services..."

# Start services in parallel
./scripts/start-service.sh vertex_claude 8090 vertex-claude.env &
./scripts/start-service.sh vertex_gemini 8091 vertex-gemini.env &
./scripts/start-service.sh github_models 8092 github-models.env &
./scripts/start-service.sh openrouter 8093 openrouter.env &

# Wait for services to start
sleep 5

echo "✅ All services started. Checking health..."
curl -s http://localhost:8090/health | jq .
curl -s http://localhost:8091/health | jq .
curl -s http://localhost:8092/health | jq .
curl -s http://localhost:8093/health | jq .

echo "🎯 Multi-Port Services Ready!"
```

### Service Management
```bash
#!/bin/bash
# manage-services.sh

ACTION=$1

case $ACTION in
    "start")
        ./scripts/start-all-multiport-services.sh
        ;;
    "stop")
        pkill -f "uvicorn.*:(8090|8091|8092|8093)"
        echo "🛑 All services stopped"
        ;;
    "restart")
        ./scripts/manage-services.sh stop
        sleep 2
        ./scripts/manage-services.sh start
        ;;
    "status")
        echo "Service Status:"
        netstat -tlnp | grep -E ":(8090|8091|8092|8093) "
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        ;;
esac
```

## Load Balancer / Router Configuration

### Intelligent Router (Port 8080)
Main entry point that routes requests to appropriate services:

```python
class IntelligentRouter:
    def __init__(self):
        self.services = {
            8090: "http://localhost:8090",  # Vertex Claude
            8091: "http://localhost:8091",  # Vertex Gemini  
            8092: "http://localhost:8092",  # GitHub Models
            8093: "http://localhost:8093",  # OpenRouter
        }
        self.fallback_chain = [8090, 8091, 8092, 8093]
        
    async def route_request(self, request_data: dict):
        """Route request based on model, availability, and preferences"""
        for port in self.fallback_chain:
            try:
                response = await self.forward_request(port, request_data)
                if response.status_code == 200:
                    return response
            except Exception as e:
                logger.warning(f"Service {port} failed: {e}")
                continue
        raise HTTPException(status_code=503, detail="All services unavailable")
```

## Health Monitoring

### Service Health Checks
```python
class HealthMonitor:
    def __init__(self, services: dict):
        self.services = services
        self.health_status = {}
        
    async def check_all_services(self):
        """Check health of all services"""
        for port, url in self.services.items():
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{url}/health", timeout=5.0)
                    self.health_status[port] = response.status_code == 200
            except:
                self.health_status[port] = False
        return self.health_status
```

## Directory Structure

```
claude-code-multiport/
├── services/                    # Service implementations
│   ├── base_service.py         # Base service class
│   ├── vertex_claude_service.py # Port 8090 service
│   ├── vertex_gemini_service.py # Port 8091 service
│   ├── github_models_service.py # Port 8092 service
│   └── openrouter_service.py   # Port 8093 service
├── config/                     # Configuration files
│   ├── vertex-claude.env
│   ├── vertex-gemini.env
│   ├── github-models.env
│   └── openrouter.env
├── scripts/                    # Management scripts
│   ├── start-service.sh
│   ├── start-all-multiport-services.sh
│   └── manage-services.sh
├── routing/                    # Router and load balancer
│   ├── intelligent_router.py
│   └── health_monitor.py
└── deployment/                 # Deployment configurations
    ├── docker-compose.yml
    └── systemd/                # Service files
```

## Integration with Existing System

### Compatibility Layer
- Maintain existing ANTHROPIC_BASE_URL environment variable support
- Default routing to port 8090 (Vertex Claude) for backward compatibility
- Fallback chain automatically handles service failures

### Migration Strategy
1. **Phase 1**: Deploy multi-port services alongside existing system
2. **Phase 2**: Gradually migrate clients to use intelligent router
3. **Phase 3**: Decommission old proxy-based system

## Next Steps

1. Implement base service class with FastAPI + LiteLLM integration
2. Create provider-specific service implementations
3. Develop intelligent router with fallback logic
4. Set up configuration management and deployment scripts
5. Integrate with Zen MCP conversation memory system
6. Add comprehensive health monitoring and logging

This architecture provides the foundation for the multi-provider system while maximizing reuse of existing claude-code-proxy patterns and preparing for integration with Zen MCP orchestration and Graphiti persistent memory.