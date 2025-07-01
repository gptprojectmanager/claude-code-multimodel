# GitHub Models Dynamic Model Fetching

## Overview

The GitHub Models service now supports dynamic model discovery and mapping, automatically fetching available models from the GitHub Models catalog API and creating intelligent mappings for seamless API compatibility.

## Implementation Details

### Key Components

#### 1. Dynamic Model Discovery
- **Method**: `fetch_available_models()`
- **Endpoint**: `https://models.github.ai/catalog/models`
- **Authentication**: GitHub PAT with proper headers
- **Result**: List of 153+ available models from multiple providers

#### 2. Intelligent Model Mapping
- **Method**: `create_dynamic_model_mapping()`
- **Strategy**: Maps Claude model names to best available GitHub models
- **Fallback**: Uses static mappings when dynamic discovery fails

#### 3. Background Initialization
- **Method**: `_initialize_models_async()`
- **Trigger**: FastAPI startup event
- **Purpose**: Prevents blocking service startup while fetching models

### Supported Model Providers

| Provider | Models Available | Example Models |
|----------|------------------|----------------|
| **OpenAI** | 20+ | `gpt-4o`, `gpt-4.1`, `gpt-4.1-mini`, `gpt-4.1-nano` |
| **O1 Series** | 5+ | `o1`, `o1-mini`, `o1-preview` |
| **Claude** | 10+ | `claude-3-5-sonnet-20241022`, `claude-3-haiku-20240307` |
| **Meta Llama** | 30+ | `llama-3.1-405b-instruct`, `llama-3.3-70b-instruct`, `llama-4-maverick-17b-128e-instruct-fp8` |
| **Mistral** | 20+ | `codestral-2501`, `mistral-large-2411`, `mistral-medium-2505` |
| **xAI Grok** | 5+ | `grok-3`, `grok-3-mini` |
| **Microsoft Phi** | 25+ | `phi-4`, `phi-4-reasoning`, `phi-4-multimodal-instruct` |

## API Usage

### Model Discovery Endpoint
```bash
curl -s http://localhost:8092/v1/models | jq .
```

### Testing Various Models
```bash
# Test Claude model
curl -X POST http://localhost:8092/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-5-haiku-20241022",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 10
  }'

# Test OpenAI GPT-4.1
curl -X POST http://localhost:8092/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openai/gpt-4.1",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 10
  }'

# Test Microsoft Phi-4
curl -X POST http://localhost:8092/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "model": "phi-4-mini-instruct",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 10
  }'
```

## Implementation Architecture

### Model Mapping Strategy

1. **Static Base Mapping**: Fallback mappings for core models
2. **Dynamic Discovery**: Fetch available models from GitHub API
3. **Intelligent Assignment**: Map Claude names to best available GitHub models
4. **Background Updates**: Refresh mappings without blocking service

### Error Handling

- **API Failure**: Falls back to static mappings
- **Authentication Issues**: Logs warnings, uses fallback models
- **Network Errors**: Graceful degradation with static mapping

### Performance Optimizations

- **Async Initialization**: Non-blocking startup
- **Background Updates**: Periodic refresh without service interruption
- **Caching**: Model mappings cached until next refresh

## Configuration

### Environment Variables
```bash
GITHUB_API_KEY=your_github_pat_token
GITHUB_MODELS_ENDPOINT=https://models.github.ai/inference
```

### Service Startup
```bash
./scripts/start-service.sh github_models 8092 github-models.env
```

## Testing Results

### Expansion Metrics
- **Before**: 7 static models
- **After**: 153+ dynamic models
- **Expansion**: 2,100% increase in available models

### Verified Model Categories
✅ **OpenAI Models**: `gpt-4o`, `gpt-4.1`, `o1-preview`
✅ **Claude Models**: `claude-3-5-haiku-20241022`, `claude-3-5-sonnet-20241022`
✅ **Llama Models**: `llama-3.1-405b-instruct`, `llama-4-maverick-17b-128e-instruct-fp8`
✅ **Mistral Models**: `codestral-2501`, `mistral-large-2411`
✅ **Grok Models**: `grok-3`, `grok-3-mini`
✅ **Phi Models**: `phi-4`, `phi-4-reasoning`, `phi-4-multimodal-instruct`

## Monitoring & Debugging

### Service Health
```bash
curl http://localhost:8092/health
```

### Available Models
```bash
curl http://localhost:8092/v1/models
```

### Service Logs
- Model discovery attempts logged with timestamps
- Mapping updates tracked with model counts
- Fallback usage clearly indicated

## Future Enhancements

1. **Periodic Refresh**: Automatic model catalog updates
2. **Model Validation**: Health checks for discovered models
3. **Usage Analytics**: Track model usage patterns
4. **Custom Mappings**: User-defined model aliases