# Repository Migration Plan - LiteLLM Library Approach

## 🎯 Objective
Migrate the modern `claude-code-multiport` architecture (LiteLLM as library) to the main repository directory, consolidating and organizing the codebase for better maintainability.

## 🏗️ Current State Analysis

### Source: `claude-code-multiport/` (LiteLLM Library - MODERN)
```
claude-code-multiport/
├── services/                 # ✅ Modern service architecture (5 services)
│   ├── base_service.py      # ✅ Reusable FastAPI + LiteLLM base (291 lines)
│   ├── github_models_service.py # ✅ Dynamic discovery (269 lines)
│   ├── vertex_claude_service.py # ✅ us-east5 config (193 lines)
│   ├── vertex_gemini_service.py # ✅ Gemini integration (237 lines)
│   └── openrouter_service.py    # ✅ 317 models (224 lines)
├── config/                  # ✅ Template-based security system
├── scripts/                 # ✅ Deployment scripts
├── tests/                   # ✅ Service tests
├── docs/                    # ✅ Security documentation
└── venv/                    # ✅ Working environment
```

### Target: Main Directory (LiteLLM Proxy - LEGACY)
```
claude-code-multimodel/
├── proxy/                   # ❌ LEGACY - Individual provider proxies
├── core/                    # 🔄 KEEP - Intelligent routing logic
├── monitoring/              # 🔄 KEEP - Analytics systems  
├── config/                  # 🔄 MERGE - YAML configs + templates
├── llm_intelligence/        # 🔄 KEEP - Intelligence systems
└── docs/                    # 🔄 MERGE - Documentation
```

## 📋 Migration Tasks for Claude (Vertex AI Sonnet 4)

### Phase 1: Repository Structure Analysis
1. **Analyze Legacy Components**
   - Review `proxy/` directory for reusable logic
   - Evaluate `core/intelligent_proxy.py` for integration potential
   - Assess `monitoring/` systems for compatibility
   - Document `llm_intelligence/` functionality

2. **Dependency Assessment**
   - Compare `requirements.txt` files
   - Identify conflicting dependencies
   - Plan dependency consolidation
   - Check virtual environment compatibility

### Phase 2: Safe Migration Strategy
1. **Create Migration Branch**
   ```bash
   git checkout -b feature/repository-restructure
   ```

2. **Backup Current State**
   ```bash
   # Create backup of current structure
   cp -r claude-code-multiport/ backup-multiport-$(date +%Y%m%d)
   cp -r proxy/ backup-proxy-$(date +%Y%m%d)
   ```

3. **Move Modern Services to Root**
   ```bash
   # Move services to root level
   mv claude-code-multiport/services/ ./
   
   # Create new config structure
   mkdir -p config/services/
   mv claude-code-multiport/config/ config/services/
   
   # Move scripts
   mkdir -p scripts/services/
   mv claude-code-multiport/scripts/ scripts/services/
   
   # Move tests
   mkdir -p tests/services/
   mv claude-code-multiport/tests/ tests/services/
   
   # Move docs
   mv claude-code-multiport/docs/ docs/services/
   ```

### Phase 3: Integration and Cleanup
1. **Merge Configurations**
   - Consolidate environment templates
   - Merge .gitignore files
   - Update documentation paths
   - Resolve configuration conflicts

2. **Update Import Paths**
   - Fix Python import statements in services
   - Update script references
   - Correct test imports
   - Validate all paths

3. **Legacy Proxy Migration**
   - Mark `proxy/` as deprecated
   - Create migration guide from proxy to services
   - Preserve useful logic from legacy proxies
   - Archive legacy components

### Phase 4: Testing and Validation
1. **Service Functionality**
   - Test all 4 services (Vertex Claude/Gemini, GitHub Models, OpenRouter)
   - Validate API endpoints (/health, /v1/models, /v1/messages)
   - Verify configuration loading
   - Test startup scripts

2. **Integration Testing**
   - Test intelligent routing compatibility
   - Validate monitoring system integration
   - Check logging and analytics
   - Verify security configuration

### Phase 5: Documentation and Finalization
1. **Update Documentation**
   - Update README.md with new structure
   - Revise PROJECT_PROGRESS.md
   - Update security documentation
   - Create migration changelog

2. **Cleanup and Archive**
   - Remove duplicate files
   - Archive legacy components
   - Clean up temporary files
   - Optimize repository size

## 🔧 Specific Instructions for Claude (Vertex AI)

### Environment Setup
```bash
# You'll be working in: /home/sam/claude-code-multimodel/
# Vertex AI configuration is already set up for us-east5
# Use the existing venv in claude-code-multiport/venv/
```

### Key Validation Points
1. **Security**: Ensure no .env files with real credentials are committed
2. **Functionality**: All services must remain operational
3. **Integration**: Preserve existing monitoring and intelligence systems
4. **Documentation**: Maintain comprehensive documentation

### Success Criteria
- ✅ All services operational in new structure
- ✅ No duplicate functionality
- ✅ Clean, organized repository structure
- ✅ Preserved legacy functionality where valuable
- ✅ Updated documentation and security
- ✅ Successful test suite execution

## 🚧 Risk Mitigation
1. **Always work on a feature branch**
2. **Create backups before major changes**
3. **Test each phase before proceeding**
4. **Preserve git history**
5. **Maintain security standards**

## 📞 Communication Protocol
- Document all major decisions
- Report any conflicts or issues encountered
- Provide progress updates after each phase
- Ask for clarification if requirements are unclear

---

**Migration Target**: Single, clean repository with modern LiteLLM library architecture
**Timeline**: Complete migration in phases
**Priority**: Maintain functionality while improving organization