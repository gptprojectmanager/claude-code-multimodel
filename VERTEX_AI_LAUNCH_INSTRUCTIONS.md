# 🚀 LAUNCH VERTEX AI CLAUDE INSTANCE

**Repository**: claude-code-multimodel  
**Task**: Fix Shrimp Task Manager bug via Vertex AI Claude  
**Working Directory**: `/home/sam/claude-code-multimodel`

## 📋 LAUNCH SEQUENCE

### **1. Start Vertex AI Service**
```bash
cd /home/sam/claude-code-multimodel
./scripts/start-vertex.sh
```

### **2. Configure Claude Code to Use Vertex AI**
```bash
export ANTHROPIC_BASE_URL=http://localhost:8090  # Vertex AI Claude port
claude
```

### **3. Vertex AI Claude Session Command**
Once Claude Vertex AI session is active, give this instruction:

```
I need to fix a critical bug in the Shrimp Task Manager system. 

Working directory: /home/sam/mcp-shrimp-task-manager
Bug: verify_task updates completion metadata but doesn't change status from "in_progress" to "completed"

Read the files:
- /home/sam/claude-code-multimodel/VERTEX_AI_TASK_STATUS_BUG_FIX.md (complete instructions)
- /home/sam/mcp-shrimp-task-manager/data/tasks.json (shows the bug)

Then cd /home/sam/mcp-shrimp-task-manager and fix the verify_task implementation to properly update task status to "completed" when score >= 80.
```

## 🎯 EXPECTED WORKFLOW

### **Vertex AI Claude Will:**
1. **Read instructions** from VERTEX_AI_TASK_STATUS_BUG_FIX.md
2. **Switch to shrimp directory**: `cd /home/sam/mcp-shrimp-task-manager`
3. **Analyze the bug** in task status update mechanism  
4. **Fix the verify_task implementation** 
5. **Test the fix** with existing task
6. **Commit the solution**

### **Success Criteria:**
- Task `d891b202-ca14-4677-95ac-d28ccae79d83` shows status "completed"
- `list_tasks status=completed` returns completed tasks
- Memory persistence issue resolved

## ⚡ QUICK VALIDATION

After Vertex AI fixes the bug, run this to verify:
```bash
cd /home/sam/mcp-shrimp-task-manager
node -e "console.log('Completed tasks:', JSON.stringify(require('./data/tasks.json').tasks.filter(t => t.status === 'completed').map(t => ({id: t.id, name: t.name, status: t.status})), null, 2))"
```

## 🔗 COORDINATION

### **Current Status:**
- ✅ **Task 5**: Zen MCP integration completed in claude-code-multimodel
- ✅ **RACE Framework**: Cognitive router improved in mcp-shrimp-task-manager  
- 🔧 **Bug Fix**: Ready for Vertex AI Claude to fix task status persistence

### **After Bug Fix:**
- 🎯 **Phase 2**: Cognitive Tools enhancement
- 🔗 **Integration**: Merge improvements back to claude-code-multimodel
- 🚀 **Complete System**: Unified intelligent multi-provider with memory persistence

---

**Ready to launch Vertex AI Claude for bug fix mission! 🚀**