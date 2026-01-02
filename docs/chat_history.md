When the chat history grows too large for the token limit, there are four standard industry strategies you can implement. Since you are using LangGraph, these are relatively easy to plug into your existing pipeline:

1. Sliding Window (Trimming)
This is the simplest approach. You only keep the most recent $N$ messages (e.g., the last 10 turns).

Pros: Very easy to implement; keeps the most relevant context.
Cons: The agent "forgets" everything that happened at the beginning of the conversation.
2. Conversation Summarization (Recommended)
When the history reaches a certain length (e.g., 15 messages), you trigger a "Summarization Node." This node takes the oldest messages, creates a concise summary, and replaces them with a single message: "Summary of previous conversation: [Summary text]".

Pros: Preserves the "essence" of the whole conversation without the token bloat.
Cons: Some fine details might be lost in the summary.
3. Vector-Based History Retrieval (Long-Term Memory)
Instead of passing the whole history, you store all past messages in a Vector Database (like the MongoDB one you just set up). Before each turn, you search the history for messages semantically related to the current query.

Pros: Can remember things from months ago if they are relevant now.
Cons: More complex to implement; can sometimes pull in confusing "out of order" context.
4. Selective Pruning
You use an LLM to look at the history and remove "low-value" messages, such as redundant tool outputs or "thank you" messages, while keeping the core factual decisions.