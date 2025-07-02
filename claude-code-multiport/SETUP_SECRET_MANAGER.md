# 🔐 Google Secret Manager Setup Instructions

This guide explains how to set up Google Secret Manager for the Claude Code Multi-Port services, replacing insecure .env files with centralized, secure credential management.

## 📋 Prerequisites

1. **Google Cloud Project** with billing enabled
2. **gcloud CLI** installed and authenticated
3. **Appropriate IAM permissions** for Secret Manager

## 🛠️ Step 1: Enable Secret Manager API

```bash
# Enable the Secret Manager API
gcloud services enable secretmanager.googleapis.com

# Verify the API is enabled
gcloud services list --enabled --filter="name:secretmanager.googleapis.com"
```

## 🔑 Step 2: Create Secrets for Each Provider

### Vertex AI Claude Configuration (Port 8090)

```bash
gcloud secrets create claude-vertex-claude-config --data-file=/dev/stdin <<EOF
{
  "project_id": "your-project-id",
  "location": "us-east5",
  "service_account_path": "/path/to/your/service-account.json"
}
EOF
```

### Vertex AI Gemini Configuration (Port 8091)

```bash
gcloud secrets create claude-vertex-gemini-config --data-file=/dev/stdin <<EOF
{
  "project_id": "your-project-id", 
  "location": "us-east5",
  "service_account_path": "/path/to/your/service-account.json"
}
EOF
```

### GitHub Models Configuration (Port 8092)

```bash
gcloud secrets create claude-github-models-config --data-file=/dev/stdin <<EOF
{
  "github_token": "your-github-personal-access-token",
  "base_url": "https://models.github.ai"
}
EOF
```

### OpenRouter Configuration (Port 8093) - NEW API KEY REQUIRED

⚠️ **CRITICAL**: Use a NEW OpenRouter API key (the old one was compromised)

```bash
gcloud secrets create claude-openrouter-config --data-file=/dev/stdin <<EOF
{
  "api_key": "your-new-openrouter-api-key",
  "base_url": "https://openrouter.ai/api/v1"
}
EOF
```

## 🔒 Step 3: Set IAM Permissions

Grant the service account access to Secret Manager:

```bash
# Replace with your actual project ID and service account email
PROJECT_ID="your-project-id"
SERVICE_ACCOUNT_EMAIL="your-service-account@your-project-id.iam.gserviceaccount.com"

# Grant Secret Manager Secret Accessor role
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/secretmanager.secretAccessor"

# Verify the permissions
gcloud projects get-iam-policy $PROJECT_ID \
    --flatten="bindings[].members" \
    --format="table(bindings.role)" \
    --filter="bindings.members:$SERVICE_ACCOUNT_EMAIL"
```

## 🧪 Step 4: Test Secret Manager Access

Run the connectivity test:

```bash
cd claude-code-multiport
python3 test_secret_manager.py
```

Expected output:
```
🔐 Claude Code Multi-Port Secret Manager Test
==================================================

📋 TEST 1: Secret Manager Connectivity
------------------------------
Project ID: your-project-id
Overall Status: healthy
Timestamp: 1735824000.0

📋 TEST 2: Provider Configuration Details
----------------------------------------
✅ vertex_claude    | Keys: ['project_id', 'location', 'service_account_path']
✅ vertex_gemini    | Keys: ['project_id', 'location', 'service_account_path']
✅ github_models    | Keys: ['github_token', 'base_url']
✅ openrouter       | Keys: ['api_key', 'base_url']

🎉 ALL TESTS PASSED! Secret Manager is ready for production.
```

## 🚀 Step 5: Start Services with Secret Manager

Start individual services:

```bash
# Start Vertex Claude service (will use Secret Manager automatically)
./scripts/start-service.sh vertex_claude 8090

# Start Vertex Gemini service
./scripts/start-service.sh vertex_gemini 8091

# Start GitHub Models service
./scripts/start-service.sh github_models 8092

# Start OpenRouter service (with NEW API key)
./scripts/start-service.sh openrouter 8093
```

Or start all services:

```bash
./scripts/start-all-services.sh
```

## 🔍 Step 6: Verify Services are Running

Test each endpoint:

```bash
# Health checks
curl http://localhost:8090/health  # Vertex Claude
curl http://localhost:8091/health  # Vertex Gemini  
curl http://localhost:8092/health  # GitHub Models
curl http://localhost:8093/health  # OpenRouter

# Model lists
curl http://localhost:8090/v1/models  # Vertex Claude models
curl http://localhost:8091/v1/models  # Vertex Gemini models
curl http://localhost:8092/v1/models  # GitHub Models
curl http://localhost:8093/v1/models  # OpenRouter models
```

## 🛡️ Security Best Practices

### Secret Rotation

Update secrets regularly:

```bash
# Update a secret (example: OpenRouter)
gcloud secrets versions add claude-openrouter-config --data-file=/dev/stdin <<EOF
{
  "api_key": "your-updated-openrouter-api-key",
  "base_url": "https://openrouter.ai/api/v1"
}
EOF
```

### Access Logging

Enable audit logs for Secret Manager:

```bash
# Create audit logging policy
cat > audit-policy.yaml <<EOF
auditConfigs:
- service: secretmanager.googleapis.com
  auditLogConfigs:
  - logType: DATA_READ
  - logType: DATA_WRITE
  - logType: ADMIN_READ
EOF

gcloud logging sinks create secret-manager-audit \
    bigquery.googleapis.com/projects/$PROJECT_ID/datasets/audit_logs \
    --log-filter='protoPayload.serviceName="secretmanager.googleapis.com"'
```

### Monitor Secret Access

View secret access logs:

```bash
gcloud logging read '
resource.type="secretmanager.googleapis.com/Secret"
protoPayload.methodName="google.cloud.secretmanager.v1.SecretManagerService.AccessSecretVersion"
' --limit=10 --format="table(timestamp,protoPayload.authenticationInfo.principalEmail,protoPayload.resourceName)"
```

## 🚨 Troubleshooting

### Common Issues

1. **"Permission denied" errors**:
   ```bash
   # Check IAM permissions
   gcloud projects get-iam-policy $PROJECT_ID
   
   # Ensure service account has secretmanager.secretAccessor role
   ```

2. **"Secret not found" errors**:
   ```bash
   # List all secrets
   gcloud secrets list
   
   # Check secret exists
   gcloud secrets describe claude-vertex-claude-config
   ```

3. **"Invalid JSON" errors**:
   ```bash
   # Validate secret content
   gcloud secrets versions access latest --secret="claude-vertex-claude-config"
   ```

4. **Service authentication failures**:
   ```bash
   # Check default credentials
   gcloud auth application-default print-access-token
   
   # Or check service account key
   echo $GOOGLE_APPLICATION_CREDENTIALS
   ```

### Debug Mode

Enable debug logging:

```bash
export GOOGLE_CLOUD_LOGGING_LEVEL=DEBUG
python3 test_secret_manager.py
```

### Fallback to .env Files

If Secret Manager is unavailable, services can fall back to .env files:

```bash
# Create .env file from template
cp claude-code-multiport/config/vertex-claude.env.template \
   claude-code-multiport/config/vertex-claude.env

# Edit with your credentials (TEMPORARY ONLY)
nano claude-code-multiport/config/vertex-claude.env

# Start with fallback mode
./scripts/start-service.sh vertex_claude 8090 vertex-claude.env
```

⚠️ **IMPORTANT**: Remove .env files immediately after Secret Manager is working!

## 📊 Monitoring and Alerting

### Set up monitoring for secret access:

```bash
# Create alerting policy for excessive secret access
gcloud alpha monitoring policies create --policy-from-file=secret-access-alert.yaml
```

### Monitor service health with Secret Manager:

```bash
# Check if services can access secrets
for service in vertex_claude vertex_gemini github_models openrouter; do
    echo "Testing $service..."
    curl -s http://localhost:809${service#*_}/health | jq '.provider_status'
done
```

## 🎯 Success Criteria

✅ All secrets created in Google Secret Manager
✅ IAM permissions properly configured  
✅ All services start successfully with Secret Manager
✅ No .env files in repository
✅ Health checks pass for all services
✅ API endpoints respond correctly
✅ No credentials in git history or logs

---

**🔐 SECURITY NOTICE**: This migration eliminates the OpenRouter API key exposure vulnerability and implements enterprise-grade secret management. All credentials are now centrally managed, auditable, and rotatable through Google Secret Manager.