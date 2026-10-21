# Shared AI-repo rules (name keywords, topics, description pattern). Fixed BEFORE list 2 was looked at; used by ai_repos_classify.py (2025 pool)
# and ai_repos_classify_sample.py (2023-2024 sample pool) so both apply exactly the same definition.
import re
NAME_TOKENS = "llm|llms|gpt|agent|agents|rag|diffusion|transformers|embedding|embeddings|mcp|genai|chatbot|copilot|ai|ml"
NAME_SUBSTR = "langchain|llamaindex|ollama|llama|openai|chatgpt|anthropic|claude|huggingface|stable-diffusion|deepseek|langgraph|autogen|crewai"
NAME_RE = re.compile(rf"(^|[^a-z0-9])({NAME_TOKENS})([^a-z0-9]|$)|({NAME_SUBSTR})")
TOPICS = set("""ai artificial-intelligence machine-learning deep-learning llm llms large-language-models generative-ai genai gpt chatgpt
openai anthropic claude gemini deepseek llama ollama langchain rag retrieval-augmented-generation mcp mcp-server mcp-servers
model-context-protocol pytorch tensorflow keras transformers huggingface diffusion stable-diffusion nlp natural-language-processing
computer-vision neural-network neural-networks reinforcement-learning text-to-image speech-recognition text-to-speech vector-database
embeddings prompt-engineering ai-agents ai-agent llm-agents agentic agentic-ai copilot""".split())
DESC_RE = re.compile(r"\b(llms?|gpt|chatgpt|openai|ai|artificial intelligence|machine learning|deep learning|neural networks?|language models?|"
                     r"ai agents?|retrieval[- ]augmented|model context protocol|mcp servers?|diffusion models?|generative ai)\b", re.I)
