import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

LLM_CFG = {
    'deepseek-v4-flash': dict(
        model='deepseek-v4-flash',
        api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL"),
    ),
    'deepseek-v4-pro': dict(
        model='deepseek-v4-pro',
        api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL"),
    ),
    'kimi-k2.6': dict(
        model='kimi-k2.6',
        api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL"),
    ),
    'kimi-k2.7': dict(
        model='kimi-k2.7',
        api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL"),
    ),
    'glm-5.1': dict(
        model='glm-5.1',
        api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL"),
    ),
    'glm-5.2': dict(
        model='glm-5.2',
        api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL"),
    ),
    'mimo-v2.5': dict(
        model='mimo-v2.5',
        api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL"),
    ),
    'mimo-v2.5-pro': dict(
        model='mimo-v2.5-pro',
        api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL"),
    ),
}

if __name__ == "__main__":
    print(BASE_DIR)
    print(LLM_CFG)
