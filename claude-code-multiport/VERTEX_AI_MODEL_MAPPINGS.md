# 🔵 Vertex AI Claude Model Mappings

**Updated**: 2025-07-02  
**Status**: ✅ Corrected according to official documentation  
**LiteLLM Compatibility**: Verified

## 📊 Correct Model Mappings

### Claude 4 Family (Latest - 2025)

| Input Model | Vertex AI Model | LiteLLM Format | Priority |
|-------------|-----------------|----------------|----------|
| `claude-opus-4` | `claude-opus-4@20250514` | `vertex_ai/claude-opus-4@20250514` | **Highest** |
| `claude-sonnet-4` | `claude-sonnet-4@20250514` | `vertex_ai/claude-sonnet-4@20250514` | **Highest** |
| `claude-4-opus` | `claude-opus-4@20250514` | `vertex_ai/claude-opus-4@20250514` | **Highest** |
| `anthropic/claude-sonnet-4` | `claude-sonnet-4@20250514` | `vertex_ai/claude-sonnet-4@20250514` | **Highest** |

### Claude 3.7 Family (Extended Thinking)

| Input Model | Vertex AI Model | LiteLLM Format | Priority |
|-------------|-----------------|----------------|----------|
| `claude-3-7-sonnet` | `claude-3-7-sonnet@20250219` | `vertex_ai/claude-3-7-sonnet@20250219` | **High** |
| `claude-3.7-sonnet` | `claude-3-7-sonnet@20250219` | `vertex_ai/claude-3-7-sonnet@20250219` | **High** |

### Claude 3.5 Family (Current Stable)

| Input Model | Vertex AI Model | LiteLLM Format | Priority |
|-------------|-----------------|----------------|----------|
| `claude-3-5-sonnet-20241022` | `claude-3-5-sonnet@20241022` | `vertex_ai/claude-3-5-sonnet@20241022` | **Medium** |
| `claude-3-5-sonnet-v2` | `claude-3-5-sonnet@20241022` | `vertex_ai/claude-3-5-sonnet@20241022` | **Medium** |
| `claude-3-5-sonnet` | `claude-3-5-sonnet@20241022` | `vertex_ai/claude-3-5-sonnet@20241022` | **Medium** |
| `claude-3-5-haiku-20241022` | `claude-3-5-haiku@20241022` | `vertex_ai/claude-3-5-haiku@20241022` | **Medium** |
| `claude-3-5-haiku` | `claude-3-5-haiku@20241022` | `vertex_ai/claude-3-5-haiku@20241022` | **Medium** |

### Claude 3 Family (Legacy)

| Input Model | Vertex AI Model | LiteLLM Format | Priority |
|-------------|-----------------|----------------|----------|
| `claude-3-opus` | `claude-3-opus@20240229` | `vertex_ai/claude-3-opus@20240229` | Low |
| `claude-3-sonnet` | `claude-3-sonnet@20240229` | `vertex_ai/claude-3-sonnet@20240229` | Low |
| `claude-3-haiku` | `claude-3-haiku@20240307` | `vertex_ai/claude-3-haiku@20240307` | Low |

## 🔧 Implementation Details

### Service Configuration

```python
# claude-code-multiport/services/vertex_claude_service.py
config = {
    "models": {
        # Claude 4 family (latest - highest priority)
        "claude-opus-4": "claude-opus-4@20250514",
        "claude-sonnet-4": "claude-sonnet-4@20250514", 
        "claude-4-opus": "claude-opus-4@20250514",
        "claude-4-sonnet": "claude-sonnet-4@20250514",
        "anthropic/claude-sonnet-4": "claude-sonnet-4@20250514",
        
        # Claude 3.7 family (extended thinking)
        "claude-3-7-sonnet": "claude-3-7-sonnet@20250219",
        "claude-3.7-sonnet": "claude-3-7-sonnet@20250219",
        
        # Claude 3.5 family  
        "claude-3-5-sonnet-20241022": "claude-3-5-sonnet@20241022",
        "claude-3-5-sonnet-v2": "claude-3-5-sonnet@20241022",
        "claude-3-5-sonnet": "claude-3-5-sonnet@20241022",
        "claude-3-5-haiku-20241022": "claude-3-5-haiku@20241022",
        "claude-3-5-haiku": "claude-3-5-haiku@20241022",
        
        # Claude 3 family (fallback)
        "claude-3-opus": "claude-3-opus@20240229",
        "claude-3-sonnet": "claude-3-sonnet@20240229", 
        "claude-3-haiku": "claude-3-haiku@20240307"
    }
}
```

### Pattern-Based Fallback Logic

```python
async def map_model(self, model: str) -> str:
    """Map Claude model names to Vertex AI format"""
    
    # Pattern-based mapping (prioritize newest)
    if 'opus-4' in clean_model.lower() or 'opus4' in clean_model.lower():
        return "vertex_ai/claude-opus-4@20250514"
    elif 'sonnet-4' in clean_model.lower() or 'sonnet4' in clean_model.lower():
        return "vertex_ai/claude-sonnet-4@20250514"
    elif '3.7' in clean_model.lower() or '3-7' in clean_model.lower():
        return "vertex_ai/claude-3-7-sonnet@20250219"
    elif 'sonnet' in clean_model.lower():
        return "vertex_ai/claude-3-5-sonnet@20241022"
    elif 'haiku' in clean_model.lower():
        return "vertex_ai/claude-3-5-haiku@20241022"
    elif 'opus' in clean_model.lower():
        return "vertex_ai/claude-3-opus@20240229"
        
    # Default to Sonnet 4 (newest)
    return "vertex_ai/claude-sonnet-4@20250514"
```

## 📚 Official Documentation Sources

### Google Cloud Vertex AI
- **Claude Models**: https://cloud.google.com/vertex-ai/generative-ai/docs/partner-models/claude
- **Claude Usage**: https://cloud.google.com/vertex-ai/generative-ai/docs/partner-models/claude/use-claude

### LiteLLM Documentation  
- **Vertex AI Provider**: https://docs.litellm.ai/docs/providers/vertex
- **Model Naming**: Requires `vertex_ai/` prefix for all Vertex AI models

### Anthropic Documentation
- **Vertex AI API**: https://docs.anthropic.com/en/api/claude-on-vertex-ai

## 🚨 Common Issues & Solutions

### Issue 1: Incorrect Model Names
**Problem**: Using `claude-3-5-sonnet-v2@20241022` instead of `claude-3-5-sonnet@20241022`
**Solution**: Remove `-v2` suffix, use official Vertex AI model names

### Issue 2: Missing `vertex_ai/` Prefix
**Problem**: LiteLLM cannot find model without provider prefix
**Solution**: Always use `vertex_ai/model-name@version` format

### Issue 3: Outdated Version Suffixes
**Problem**: Using old version dates like `@20240620`
**Solution**: Use current versions as documented above

### Issue 4: Region Availability
**Problem**: Not all models available in all regions
**Solution**: Use `us-east5` for broadest Claude model availability

## 🧪 Testing Model Mappings

### Run Test Suite
```bash
cd claude-code-multiport
python3 test_vertex_models.py
```

### Manual Testing
```bash
# Test individual model mapping
python3 -c "
from services.vertex_claude_service import VertexClaudeService
import asyncio

async def test():
    service = VertexClaudeService()
    mapped = await service.map_model('claude-sonnet-4')
    print(f'Mapped: {mapped}')
    
asyncio.run(test())
"
```

### Expected Output
```
✅ claude-sonnet-4 → vertex_ai/claude-sonnet-4@20250514
✅ claude-3-7-sonnet → vertex_ai/claude-3-7-sonnet@20250219
✅ claude-3-5-sonnet → vertex_ai/claude-3-5-sonnet@20241022
```

## 🔄 Update History

### 2025-07-02: Major Correction
- ❌ **Removed**: Incorrect mappings like `claude-3-5-sonnet-v2@20241022`
- ✅ **Added**: Correct Claude 4 family models (`claude-opus-4@20250514`, `claude-sonnet-4@20250514`)
- ✅ **Added**: Claude 3.7 Sonnet with extended thinking (`claude-3-7-sonnet@20250219`)
- ✅ **Updated**: All version suffixes to match official documentation
- ✅ **Verified**: LiteLLM compatibility with `vertex_ai/` prefix

### Key Changes Made
1. **Model Names**: Updated to official Vertex AI model identifiers
2. **Version Suffixes**: Corrected to match Google Cloud documentation  
3. **Priority**: Claude 4 > Claude 3.7 > Claude 3.5 > Claude 3
4. **Fallback Logic**: Enhanced pattern matching for better model selection

## 🎯 Next Steps

1. **Test Service**: Run `./scripts/start-service.sh vertex_claude 8090`
2. **Verify API**: Test with `curl http://localhost:8090/v1/models`
3. **Monitor Logs**: Check for successful model mappings
4. **Update Other Services**: Apply similar corrections to Gemini service if needed

---

*Model mappings verified against official Google Cloud and LiteLLM documentation*