# 🔐 VERTEX AI CLAUDE INSTRUCTIONS: Google Secret Manager Migration

**Created**: 2025-07-02  
**Priority**: 🔴 CRITICAL SECURITY  
**Project**: claude-code-multimodel  
**Issue**: OpenRouter API key exposed in public repository - need migration to Google Secret Manager

## 📋 COMMAND FOR VERTEX AI CLAUDE

```
I need you to implement a complete migration from .env files to Google Secret Manager for the claude-code-multimodel project. This is a critical security task following an API key exposure incident.

Working directory: /home/sam/claude-code-multimodel
Priority: CRITICAL - eliminate .env file security risks
Target: Replace all .env files with Google Secret Manager integration

Follow the implementation plan below step by step.
```

## 🚨 SECURITY INCIDENT CONTEXT

### **Problem Identified**
- **Location**: OpenRouter API key exposed in commit 47bc1c9
- **File**: claude-code-multiport/config/openrouter.env
- **Impact**: API key compromised and disabled by OpenRouter
- **Risk**: All .env files pose similar exposure risk

### **Current Vulnerable Files**
```
claude-code-multiport/config/
├── vertex-claude.env          # ❌ Contains Google Cloud credentials
├── vertex-gemini.env          # ❌ Contains Google Cloud credentials  
├── github-models.env          # ❌ Contains GitHub tokens
└── openrouter.env             # ❌ Contains API keys (already compromised)
```

## 🎯 MIGRATION OBJECTIVES

### **Primary Goals**
1. **Eliminate .env files** - Remove all local credential storage
2. **Implement Google Secret Manager** - Centralized, secure credential management
3. **Update all services** - Modify code to read from Secret Manager
4. **Security hardening** - Implement best practices and monitoring

### **Success Criteria**
- ✅ No credentials in repository (local or remote)
- ✅ All services use Google Secret Manager
- ✅ Services start successfully with Secret Manager
- ✅ No functionality regression
- ✅ Security audit compliance

## 📋 IMPLEMENTATION PLAN

### **STEP 1: Google Secret Manager Setup**

#### **1.1 Enable Secret Manager API**
```bash
gcloud services enable secretmanager.googleapis.com
```

#### **1.2 Create Secret Structure**
Create secrets for each provider with this naming convention:
```bash
# Vertex AI Claude (Port 8090)
gcloud secrets create claude-vertex-claude-config --data-file=/dev/stdin <<EOF
{
  "project_id": "your-project-id",
  "location": "us-east5", 
  "service_account_path": "/path/to/service-account.json"
}
EOF

# Vertex AI Gemini (Port 8091)  
gcloud secrets create claude-vertex-gemini-config --data-file=/dev/stdin <<EOF
{
  "project_id": "your-project-id",
  "location": "us-east5",
  "service_account_path": "/path/to/service-account.json"
}
EOF

# GitHub Models (Port 8092)
gcloud secrets create claude-github-models-config --data-file=/dev/stdin <<EOF
{
  "github_token": "your-github-token",
  "base_url": "https://models.inference.ai.azure.com"
}
EOF

# OpenRouter (Port 8093) - REPLACE WITH NEW KEY
gcloud secrets create claude-openrouter-config --data-file=/dev/stdin <<EOF
{
  "api_key": "your-new-openrouter-key",
  "base_url": "https://openrouter.ai/api/v1"
}
EOF
```

#### **1.3 Set IAM Permissions**
```bash
# Grant Secret Manager access to compute service account
gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" \
    --role="roles/secretmanager.secretAccessor"
```

### **STEP 2: Code Migration**

#### **2.1 Create Secret Manager Client**
Create `claude-code-multiport/utils/secret_manager.py`:
```python
from google.cloud import secretmanager
import json
import os
from typing import Dict, Any
import logging

class SecretManagerClient:
    def __init__(self, project_id: str = None):
        self.project_id = project_id or os.getenv('GOOGLE_CLOUD_PROJECT')
        self.client = secretmanager.SecretManagerServiceClient()
        
    def get_secret(self, secret_name: str, version: str = "latest") -> Dict[str, Any]:
        """Retrieve and parse secret from Secret Manager"""
        try:
            name = f"projects/{self.project_id}/secrets/{secret_name}/versions/{version}"
            response = self.client.access_secret_version(request={"name": name})
            secret_data = response.payload.data.decode("UTF-8")
            return json.loads(secret_data)
        except Exception as e:
            logging.error(f"Failed to retrieve secret {secret_name}: {e}")
            raise
            
    def get_provider_config(self, provider: str) -> Dict[str, Any]:
        """Get configuration for specific provider"""
        secret_mapping = {
            "vertex_claude": "claude-vertex-claude-config",
            "vertex_gemini": "claude-vertex-gemini-config", 
            "github_models": "claude-github-models-config",
            "openrouter": "claude-openrouter-config"
        }
        
        secret_name = secret_mapping.get(provider)
        if not secret_name:
            raise ValueError(f"Unknown provider: {provider}")
            
        return self.get_secret(secret_name)
```

#### **2.2 Update Service Files**
Modify each service in `claude-code-multiport/services/` to use Secret Manager:

**Example for `vertex_claude_service.py`:**
```python
from utils.secret_manager import SecretManagerClient

class VertexClaudeService(BaseMultiPortService):
    def __init__(self):
        super().__init__()
        self.secret_client = SecretManagerClient()
        self.config = self.secret_client.get_provider_config("vertex_claude")
        
    def setup_litellm(self):
        # Use config from Secret Manager instead of .env file
        os.environ["VERTEX_PROJECT"] = self.config["project_id"]
        os.environ["VERTEX_LOCATION"] = self.config["location"]
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.config["service_account_path"]
        # ... rest of setup
```

#### **2.3 Update All Services**
Apply similar changes to:
- `vertex_gemini_service.py`
- `github_models_service.py`  
- `openrouter_service.py`

### **STEP 3: Remove .env Files**

#### **3.1 Delete .env Files**
```bash
# Remove actual credential files
rm claude-code-multiport/config/*.env

# Keep only templates for documentation
git rm claude-code-multiport/config/*.env
git add claude-code-multiport/config/*.env.template
```

#### **3.2 Update .gitignore**
```bash
echo "# Credentials - use Google Secret Manager instead" >> .gitignore
echo "*.env" >> .gitignore
echo "!*.env.template" >> .gitignore
echo "service-account*.json" >> .gitignore
```

### **STEP 4: Update Dependencies**

#### **4.1 Add Secret Manager Dependency**
Update `claude-code-multiport/requirements.txt`:
```
google-cloud-secret-manager>=2.16.0
```

#### **4.2 Update Scripts**
Modify `claude-code-multiport/scripts/start-service.sh` to check Secret Manager access:
```bash
#!/bin/bash
# Check Secret Manager access before starting services
echo "🔐 Checking Google Secret Manager access..."
python3 -c "
from utils.secret_manager import SecretManagerClient
client = SecretManagerClient()
print('✅ Secret Manager access verified')
"
```

### **STEP 5: Testing and Validation**

#### **5.1 Test Each Service**
```bash
cd claude-code-multiport

# Test Secret Manager access
python3 -c "
from utils.secret_manager import SecretManagerClient
client = SecretManagerClient()
for provider in ['vertex_claude', 'vertex_gemini', 'github_models', 'openrouter']:
    config = client.get_provider_config(provider)
    print(f'✅ {provider}: {list(config.keys())}')
"

# Test service startup
./scripts/start-service.sh vertex_claude 8090
./scripts/start-service.sh vertex_gemini 8091
./scripts/start-service.sh github_models 8092
./scripts/start-service.sh openrouter 8093
```

#### **5.2 Validate No Credentials in Repository**
```bash
# Scan for potential credential patterns
git log --all -S "sk-" --source --all
git log --all -S "ghp_" --source --all  
git log --all -S "api_key" --source --all
```

## 🔧 IMPLEMENTATION CHECKLIST

### **Secret Manager Setup**
- [ ] Enable Secret Manager API
- [ ] Create secrets for all 4 providers
- [ ] Set IAM permissions for service account
- [ ] Test secret access from compute environment

### **Code Migration**
- [ ] Create `utils/secret_manager.py` client
- [ ] Update `vertex_claude_service.py`
- [ ] Update `vertex_gemini_service.py`
- [ ] Update `github_models_service.py`
- [ ] Update `openrouter_service.py` (with NEW API key)
- [ ] Update `base_service.py` if needed

### **Security Cleanup**
- [ ] Delete all `.env` files from working directory
- [ ] Remove `.env` files from git tracking
- [ ] Update `.gitignore` to prevent future .env commits
- [ ] Add Secret Manager dependency to requirements.txt

### **Testing and Validation**
- [ ] Test Secret Manager client functionality
- [ ] Test each service startup with Secret Manager
- [ ] Validate API endpoints work correctly
- [ ] Confirm no credentials in repository
- [ ] Test service restart and recovery

### **Documentation and Deployment**
- [ ] Update service README with Secret Manager instructions
- [ ] Update deployment scripts
- [ ] Document secret management procedures
- [ ] Create monitoring/alerting for secret access

## 🚨 SECURITY REQUIREMENTS

### **Critical Security Measures**
1. **No credentials in code** - Ever, anywhere
2. **Secret rotation capability** - Easy to update secrets
3. **Access logging** - Monitor secret access
4. **Principle of least privilege** - Minimal required permissions
5. **Environment isolation** - Dev/prod secret separation

### **Post-Migration Security Checklist**
- [ ] No API keys, tokens, or credentials in any file
- [ ] No credentials in git history (scan completed)
- [ ] All services use Secret Manager exclusively
- [ ] IAM permissions follow least privilege
- [ ] Secret access is logged and monitored
- [ ] Backup/recovery procedures documented

## 🎯 ACCEPTANCE CRITERIA

### **Functional Requirements**
1. **All services start successfully** using Secret Manager
2. **API endpoints work** exactly as before
3. **No regression** in functionality or performance
4. **Health checks pass** for all 4 services
5. **Fallback chain works** (Vertex → GitHub → OpenRouter)

### **Security Requirements**
1. **Zero credentials in repository** (local and remote)
2. **Secret Manager integration** working for all providers
3. **IAM properly configured** with minimal permissions
4. **Audit trail enabled** for secret access
5. **Emergency rotation procedures** documented

## 🔗 RESOURCES AND REFERENCES

### **Google Secret Manager Documentation**
- [Secret Manager Overview](https://cloud.google.com/secret-manager/docs)
- [Python Client Library](https://cloud.google.com/secret-manager/docs/reference/libraries#client-libraries-usage-python)
- [IAM and Access Control](https://cloud.google.com/secret-manager/docs/access-control)

### **Security Best Practices**
- [Google Cloud Security Best Practices](https://cloud.google.com/security/best-practices)
- [Secret Management Best Practices](https://cloud.google.com/secret-manager/docs/best-practices)

## 🚀 COMPLETION INSTRUCTIONS

### **When Done:**
1. **Commit Changes**:
   ```bash
   git add .
   git commit -m "🔐 SECURITY: Migrate to Google Secret Manager
   
   • Eliminated all .env files and local credential storage
   • Implemented Google Secret Manager integration for all providers
   • Updated services: vertex_claude, vertex_gemini, github_models, openrouter
   • Added secret_manager.py client with provider config management
   • Updated dependencies and deployment scripts
   • Removed credential files from git tracking
   • Enhanced .gitignore to prevent future credential exposure
   
   Security improvements:
   • Zero credentials in repository (local/remote)
   • Centralized secret management with Google Secret Manager
   • IAM-controlled access with least privilege
   • Audit trail for all secret access
   • Emergency rotation capability
   
   Resolves: OpenRouter API key exposure incident
   
   🤖 Generated with Claude Code
   Co-Authored-By: Claude <noreply@anthropic.com>"
   ```

2. **Test Complete System**:
   ```bash
   # Start all services and verify functionality
   cd claude-code-multiport
   ./scripts/start-all-services.sh
   
   # Test each endpoint
   curl http://localhost:8090/health  # Vertex Claude
   curl http://localhost:8091/health  # Vertex Gemini
   curl http://localhost:8092/health  # GitHub Models
   curl http://localhost:8093/health  # OpenRouter (NEW key)
   ```

3. **Security Validation**:
   ```bash
   # Confirm no credentials in repository
   grep -r "sk-" . || echo "✅ No OpenAI keys found"
   grep -r "ghp_" . || echo "✅ No GitHub tokens found"
   grep -r "api_key" . || echo "✅ No api_key patterns found"
   ```

4. **Documentation Update**:
   Create `SECURITY_MIGRATION_REPORT.md` documenting the migration and new security posture.

## 📞 EMERGENCY CONTACT

If you encounter issues during migration:
1. **Document the problem** in a `SECRET_MANAGER_DEBUG.md` file
2. **Show current state** vs expected state  
3. **List Secret Manager errors** and IAM permission issues
4. **Preserve service functionality** - rollback if necessary

**CRITICAL**: This migration eliminates a major security vulnerability. Complete it thoroughly and test extensively before deployment.

---

*Security Migration Instructions for Vertex AI Claude - Generated 2025-07-02*