# Instructions for Claude (Vertex AI Sonnet 4) - Repository Migration

## 🤖 Context and Role
You are a specialized Claude instance running on Vertex AI with Sonnet 4, tasked with migrating and reorganizing the `claude-code-multimodel` repository from a mixed architecture to a clean, modern LiteLLM library-based structure.

## 📁 Current Working Environment
- **Repository**: `/home/sam/claude-code-multimodel/`
- **Primary Branch**: `master`
- **Virtual Environment**: `claude-code-multiport/venv/` (Python 3.12)
- **Authentication**: Vertex AI us-east5 (already configured)

## 🎯 Your Mission
Migrate the modern `claude-code-multiport` microservices architecture to the main repository directory, replacing the legacy proxy approach while preserving valuable existing functionality.

## 📋 Detailed Task Breakdown

### Phase 1: Repository Analysis (FIRST PRIORITY)
Execute these exact commands and analyze the results:

```bash
# 1. Understand current structure
pwd
ls -la
git status
git log --oneline -5

# 2. Analyze legacy proxy implementation
head -50 proxy/claude_anthropic_proxy.py
ls proxy/
wc -l proxy/*.py

# 3. Analyze modern multiport implementation  
head -50 claude-code-multiport/services/base_service.py
ls claude-code-multiport/services/
wc -l claude-code-multiport/services/*.py

# 4. Check for conflicts and dependencies
diff requirements.txt claude-code-multiport/requirements.txt || echo "Files differ"
ls config/
ls claude-code-multiport/config/
```

**Your Analysis Task**: After running these commands, provide a detailed report on:
- Functionality differences between proxy/ and services/
- Dependencies that need consolidation
- Configuration conflicts to resolve
- Valuable legacy components to preserve

### Phase 2: Safe Migration Strategy

```bash
# 1. Create migration branch
git checkout -b feature/repository-restructure-$(date +%Y%m%d)

# 2. Create comprehensive backup
mkdir -p migration-backup-$(date +%Y%m%d-%H%M)
cp -r claude-code-multiport/ migration-backup-$(date +%Y%m%d-%H%M)/
cp -r proxy/ migration-backup-$(date +%Y%m%d-%H%M)/
cp -r config/ migration-backup-$(date +%Y%m%d-%H%M)/
echo "✅ Backup created in migration-backup-$(date +%Y%m%d-%H%M)/"
```

### Phase 3: Execute Migration

```bash
# 1. Move modern services to root (BE VERY CAREFUL)
mv claude-code-multiport/services/ ./services-new/
mv claude-code-multiport/requirements.txt ./requirements-services.txt

# 2. Create organized config structure
mkdir -p config/services/
cp -r claude-code-multiport/config/ config/services/

# 3. Move supporting infrastructure
mkdir -p scripts/services/
cp -r claude-code-multiport/scripts/ scripts/services/

mkdir -p tests/services/
cp -r claude-code-multiport/tests/ tests/services/

mkdir -p docs/services/
cp -r claude-code-multiport/docs/ docs/services/
```

### Phase 4: Integration and Cleanup

**Critical Tasks**:
1. **Merge requirements.txt files** - Consolidate dependencies
2. **Update Python import paths** - Fix all import statements
3. **Resolve configuration conflicts** - Merge .env templates
4. **Test service functionality** - Ensure all services work

```bash
# Test that services still work after migration
cd /home/sam/claude-code-multimodel/
source claude-code-multiport/venv/bin/activate

# Update Python path and test imports
export PYTHONPATH="/home/sam/claude-code-multimodel:$PYTHONPATH"
python3 -c "from services-new.base_service import BaseMultiPortService; print('✅ Import successful')"
```

### Phase 5: Validation and Testing

**MANDATORY TESTS**:
```bash
# 1. Test all services
python3 -c "
import sys
sys.path.append('./services-new')
from vertex_claude_service import VertexClaudeService
from openrouter_service import OpenRouterService  
from github_models_service import GitHubModelsService

print('✅ All services importable')
"

# 2. Test configuration loading
./scripts/services/start-service.sh openrouter 8093 openrouter.env &
sleep 5
curl -s http://localhost:8093/health | jq .
pkill -f openrouter
```

## 🔐 Security Requirements (CRITICAL)

### Mandatory Security Checks
```bash
# 1. Verify no .env files are staged
git status | grep "\.env$" && echo "❌ STOP: .env files detected" || echo "✅ No .env files staged"

# 2. Check for API keys in staged files
git diff --cached | grep -i "sk-\|ghp_\|pat_" && echo "❌ STOP: API keys detected" || echo "✅ No API keys found"

# 3. Verify .gitignore protection
echo "test-key=sk-test-123" > config/services/test.env
git status | grep "test.env" && echo "❌ STOP: .gitignore not working" || echo "✅ .gitignore working"
rm config/services/test.env
```

**STOP IMMEDIATELY** if any security check fails and report the issue.

## 📊 Required Deliverables

### 1. Migration Report
Create `/home/sam/claude-code-multimodel/MIGRATION_REPORT.md` with:
- Summary of changes made
- Files moved/modified/deleted
- Import path updates
- Configuration changes
- Any issues encountered

### 2. Functionality Verification
Provide test results for:
- All 4 services (Vertex Claude/Gemini, GitHub Models, OpenRouter)
- Configuration loading
- Security measures
- Import resolution

### 3. Cleanup Summary
Report on:
- Legacy files archived/removed
- Duplicate functionality eliminated
- Repository size optimization
- Documentation updates

## 🚨 Critical Guidelines

### DO NOT PROCEED if:
- Security checks fail
- Tests don't pass
- Git repository becomes corrupted
- Virtual environment breaks

### ALWAYS:
- Test each major change before proceeding
- Maintain git history
- Document all decisions
- Report progress regularly

### NEVER:
- Commit .env files with real credentials
- Break existing functionality
- Remove backups
- Force push without confirmation

## 🎯 Success Criteria

✅ **Repository Structure**: Clean, organized, no duplicates
✅ **Services**: All 4 services operational in new location
✅ **Security**: No credentials exposed, .gitignore working
✅ **Testing**: All tests pass
✅ **Documentation**: Updated and accurate

## 🤝 Communication

After completing each phase, provide:
1. **Status Update**: What was accomplished
2. **Test Results**: Service functionality verification
3. **Issues**: Any problems encountered
4. **Next Steps**: What needs attention

Remember: **Quality over speed**. Better to do this correctly than quickly.

---

**Start with Phase 1 analysis and await further instructions before proceeding to migration phases.**