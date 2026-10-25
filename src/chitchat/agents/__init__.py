"""The multi-agent loop that answers the run's question with a decision brief.

Planner (LLM) → Retriever (index search, no LLM) → Writer (LLM) → checks (no LLM) and
Critic (LLM) → more retrieval and a rewrite, until the Critic accepts or the rounds run out.
"""
