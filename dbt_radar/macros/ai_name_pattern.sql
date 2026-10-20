{#- Regex for "looks like an AI repo" applied to the repo NAME (the part after owner/).
    Short tokens must match as whole words (split on non-alphanumerics) so `rag` does not hit `storage` and `ml` does not hit `html`;
    long distinctive names also match as substrings. Measured precision ~95% on a 40-repo eyeballed sample; recall NOT measured. -#}
{% macro ai_name_pattern() -%}
(^|[^a-z0-9])(llm|llms|gpt|agent|agents|rag|diffusion|transformers|embedding|embeddings|mcp|genai|chatbot|copilot|ai|ml)([^a-z0-9]|$)|(langchain|llamaindex|ollama|llama|openai|chatgpt|anthropic|claude|huggingface|stable-diffusion|deepseek|langgraph|autogen|crewai)
{%- endmacro %}
