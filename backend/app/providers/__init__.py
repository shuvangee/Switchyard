"""AI provider adapters.

Each provider (OpenAI, Anthropic, Google, mock, ...) implements a common
interface here so routing and evaluation code never depends on a specific
vendor SDK directly. Implemented starting in V0.
"""
