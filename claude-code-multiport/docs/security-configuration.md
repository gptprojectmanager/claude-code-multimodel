# Security Configuration Guide

## 🔒 Configuration Management

### Template System
This project uses a template-based configuration system to prevent accidentally committing sensitive information.

```
config/
├── openrouter.env.template     ✅ Safe to commit (no real keys)
├── vertex-claude.env.template  ✅ Safe to commit (no real keys)  
├── vertex-gemini.env.template  ✅ Safe to commit (no real keys)
├── github-models.env.template  ✅ Safe to commit (no real keys)
├── openrouter.env             ❌ Local only (real API keys)
├── vertex-claude.env          ❌ Local only (real project IDs)
├── vertex-gemini.env          ❌ Local only (real project IDs)
└── github-models.env          ❌ Local only (real tokens)
```

### Setup Process

1. **Copy templates to create local config:**
   ```bash
   cp config/openrouter.env.template config/openrouter.env
   cp config/vertex-claude.env.template config/vertex-claude.env
   cp config/vertex-gemini.env.template config/vertex-gemini.env
   cp config/github-models.env.template config/github-models.env
   ```

2. **Edit local .env files with real credentials:**
   ```bash
   # Edit each .env file with your actual API keys
   vim config/openrouter.env     # Add real OpenRouter API key
   vim config/vertex-claude.env  # Add real Google Cloud project ID
   # etc...
   ```

3. **Verify .gitignore protection:**
   ```bash
   git status  # Should NOT show .env files as changes
   ```

## 🛡️ Security Best Practices

### API Key Management
- **OpenRouter**: Use `sk-or-v1-` prefixed keys
- **GitHub Models**: Use Personal Access Tokens (PAT) with minimal scopes
- **Vertex AI**: Use service account JSON files (also excluded from git)

### Environment Variables
```bash
# OpenRouter
OPENROUTER_API_KEY=sk-or-v1-your_actual_key_here

# GitHub Models  
GITHUB_TOKEN=ghp_your_actual_token_here

# Vertex AI
GOOGLE_CLOUD_PROJECT=your-actual-project-id
GOOGLE_APPLICATION_CREDENTIALS=./config/vertex-service-account.json
```

### Service Account Files
- Place service account JSON files in `config/` directory
- Files matching `*service-account*.json` are automatically ignored
- Never commit service account files to version control

## 🚫 What NOT to Commit

### Forbidden Files
```
# These patterns are blocked by .gitignore:
config/*.env                    # Local configuration files
*service-account*.json         # Google Cloud service accounts  
*.key, *.pem                   # Private keys
credentials.env                # Any credentials file
*local.env, *local.json       # Local overrides
```

### Forbidden Content
- API keys starting with `sk-`, `ghp_`, `pat_`
- Google Cloud project IDs  
- Service account private keys
- Database connection strings with passwords
- Any hardcoded secrets or tokens

## ✅ Safe to Commit

### Template Files
```
config/*.env.template          # Configuration templates
docs/                         # Documentation
scripts/                      # Deployment scripts (without secrets)
services/                     # Service code
tests/                        # Test files
```

### Safe Content
- Placeholder values: `your_api_key_here`
- Service endpoints: `https://openrouter.ai/api/v1`
- Configuration structure and comments
- Default values and examples

## 🔧 Maintenance

### Adding New Services
1. Create `config/newservice.env.template` with placeholders
2. Add `config/newservice.env` to `.gitignore`
3. Document setup process in this file
4. Test that real `.env` files are ignored by git

### Regular Security Checks
```bash
# Check for accidentally staged secrets
git diff --cached | grep -i "sk-\|ghp_\|pat_"

# Verify .gitignore is working
git status | grep "\.env$" || echo "✅ No .env files staged"

# Check for hardcoded secrets in code
rg "sk-|ghp_|pat_" --type py services/ || echo "✅ No secrets in code"
```

## 🚨 Security Incident Response

### If API Key is Accidentally Committed:
1. **Immediately rotate the API key** at the provider
2. Remove the key from all config files
3. Add proper `.gitignore` entries
4. Use `git rm --cached` to untrack files
5. Commit the fixes with security note
6. Update all team members

### If Key is Already Pushed:
1. **Rotate key immediately** (assume compromised)
2. Consider the repository public for that key
3. Remove key from files and push fix
4. Monitor for unusual API usage
5. Document incident in project notes

## 📋 Security Checklist

- [ ] All `.env.template` files have placeholder values
- [ ] All `.env` files are in `.gitignore`  
- [ ] No real API keys in any committed files
- [ ] Service account JSON files excluded
- [ ] Regular secret scanning of codebase
- [ ] Team trained on secure practices
- [ ] Incident response plan documented