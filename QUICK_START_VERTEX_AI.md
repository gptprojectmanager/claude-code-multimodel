# 🚀 QUICK START FOR VERTEX AI CLAUDE

**Project**: Shrimp Task Manager Bug Fix  
**Working Directory**: `/home/sam/mcp-shrimp-task-manager`  
**Priority**: CRITICAL Bug Fix

## 📋 IMMEDIATE COMMAND

```bash
cd /home/sam/mcp-shrimp-task-manager
```

Then say to Vertex AI Claude:

```
I need to fix a critical bug in this Shrimp Task Manager. Read VERTEX_AI_TASK_STATUS_BUG_FIX.md for complete instructions. The bug is that verify_task updates completion metadata but doesn't change task status from "in_progress" to "completed". Fix this immediately.
```

## 🎯 EXPECTED RESULT

After the fix:
- Tasks that score >= 80 in verify_task should have status "completed"
- The task `d891b202-ca14-4677-95ac-d28ccae79d83` should show as completed
- `list_tasks status=completed` should return completed tasks

## ⚡ VALIDATION COMMAND

```bash
# After fix, this should show completed tasks:
node -e "console.log('Completed tasks:', JSON.stringify(require('./data/tasks.json').tasks.filter(t => t.status === 'completed').map(t => ({id: t.id, name: t.name, status: t.status})), null, 2))"
```

---

**Ready for Vertex AI Claude to execute immediately!**