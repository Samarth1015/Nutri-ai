from langgraph.checkpoint.memory import MemorySaver

# A global, in-memory checkpointer to persist agent state (conversation history)
# across different webhook requests. In production, this can be swapped for 
# an AsyncPostgresSaver or RedisSaver.
agent_memory = MemorySaver()
