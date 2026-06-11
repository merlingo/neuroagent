#!/bin/sh
set -eu

for model in \
  "${OLLAMA_DEEPSEEK_R1_MODEL:-}" \
  "${OLLAMA_KIMI_K26_MODEL:-}" \
  "${OLLAMA_GLM_51_MODEL:-}" \
  "${OLLAMA_QWEN_35_MODEL:-}" \
  "${OLLAMA_QWEN25_CODER_MODEL:-}" \
  "${OLLAMA_GEMMA4_MODEL:-}"
do
  if [ -n "$model" ]; then
    ollama pull "$model"
  fi
done
