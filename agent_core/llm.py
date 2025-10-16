# agent_core/utils/llm.py
import os
from functools import lru_cache
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

MODEL_NAME = "gemini-2.5-flash"
google_api_key = os.getenv("GOOGLE_API_KEY")

if not google_api_key:
    raise ValueError("❌ GOOGLE_API_KEY not found in environment variables.")


@lru_cache(maxsize=4)
def get_model(
    temperature: float = 0.2,
    top_p: float = 0.95,
):
    """
    Create a cached, configured ChatGoogleGenerativeAI model.

    Params:
        temperature: randomness (0 = deterministic, 1 = creative)
        top_p: nucleus sampling (0.95 recommended for balance)
        system_instruction: optional role / behavior context
        json_output: if True, request JSON output format

    Returns:
        Cached LLM instance for better performance
    """
    # Configuration for faster responses
    llm = ChatGoogleGenerativeAI(
        model=MODEL_NAME,
        api_key=google_api_key,
        temperature=temperature,
        top_p=top_p,
    )

    return llm
