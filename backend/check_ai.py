"""Quick test: does the AI chatbot work with your .env settings?

Usage:  python check_ai.py "What services do you offer?"
"""
import sys

import chat
from config import Config

cfg = Config()
question = " ".join(sys.argv[1:]) or "What services do you offer and where are you located?"

print(f"Provider: {cfg.LLM_PROVIDER}")
if not chat.is_configured(cfg):
    print("Not configured: set LLM_API_KEY in .env (and LLM_MODEL for groq/openai/custom).")
    sys.exit(1)
try:
    print(f"Model:    {chat.model_name(cfg)}")
    print(f"Question: {question}\n")
    print("Answer:   " + chat.ask(cfg, [{"role": "user", "content": question}]))
except chat.LLMError as exc:
    print(f"Failed: {exc}")
    print("Check the API key, and that the model name exists for your account (see Google AI Studio for Gemini).")
    sys.exit(2)
