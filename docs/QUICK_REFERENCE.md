# Quick Reference: Memory Management

## 🎯 Quick Actions

### Clear Current Conversation Context
```
Option 1: Click "🧹 Forget Context" button in sidebar
Option 2: Type "/forget" or "/clear" in chat
```

### Start Completely New Chat
```
Click "➕ New Chat" button in sidebar
```

---

## 📊 How It Works

### Automatic Summarization

```
10-99 messages:
├─ Old messages (all except last 4) → Summary
└─ Recent messages (last 4) → Kept as-is

100+ messages:
├─ Old messages → Split into chunks of 20
│   ├─ Chunk 1 → Summary 1
│   ├─ Chunk 2 → Summary 2
│   └─ Chunk N → Summary N
├─ All chunk summaries → Meta-summary
└─ Recent messages (last 4) → Kept as-is
```

### Context Sent to Agent

```
Every query receives:
├─ Summary (compressed history)
├─ Last 6 messages (recent context)
└─ Current query
```

---

## 🔧 Commands

| Command | Action | Session ID |
|---------|--------|------------|
| `/forget` | Clear context | Stays same |
| `/clear` | Clear context | Stays same |
| New Chat button | Clear everything | Changes |

---

## 💡 When to Use What

| Scenario | Action |
|----------|--------|
| Topic switch in same session | `/forget` or Forget button |
| Start completely new project | New Chat button |
| Clear sensitive info | `/forget` or Forget button |
| Agent seems confused | `/forget` or Forget button |
| Want to preserve old chat | New Chat button |

---

## 📈 Token Savings

| Messages | Without Summarization | With Summarization | Savings |
|----------|----------------------|-------------------|---------|
| 10 | ~2,000 tokens | ~2,000 tokens | 0% |
| 50 | ~10,000 tokens | ~2,500 tokens | 75% |
| 100 | ~20,000 tokens | ~3,000 tokens | 85% |
| 200 | ~40,000 tokens | ~4,000 tokens | 90% |

*Approximate values, actual savings depend on message length*

---

## 🎨 UI Elements

```
Sidebar:
┌─────────────────────────────────┐
│ 🧠 Agent Settings               │
├─────────────────────────────────┤
│ [➕ New Chat] [🧹 Forget Context]│
│                                 │
│ Current Session ID: chat_12345  │
│                                 │
│ 📂 Previous Sessions            │
│ ...                             │
└─────────────────────────────────┘

Chat Input:
┌─────────────────────────────────┐
│ Ask me anything...              │
│ (Type /forget to clear context) │
└─────────────────────────────────┘
```

---

## ⚡ Pro Tips

1. **Long research sessions**: Let automatic summarization handle it
2. **Switching topics**: Use `/forget` to start fresh
3. **Privacy**: Clear context after discussing sensitive info
4. **Performance**: Forget context if responses slow down
5. **Organization**: Use New Chat for different projects

---

## 🔍 Monitoring

Watch the status messages:
- `🧠 Summarizing conversation history (X messages)...` - Standard summarization
- `📚 Applying hierarchical summarization...` - Advanced mode (100+ messages)
- `✅ Context cleared! Starting fresh.` - Forget command executed

---

## 📞 Support

If context clearing doesn't work:
1. Check MongoDB connection
2. Verify API is running
3. Check browser console for errors
4. Try refreshing the page
5. Restart the application

For more details, see: [MEMORY_MANAGEMENT.md](./MEMORY_MANAGEMENT.md)
