import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

LLM_CFG = {
    'kimi-k2.6': dict(
        model=os.getenv("LLM_MODEL"),
        api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL"),
    ),
    'deepseek-v4-flash': dict(
        model='deepseek-v4-flash',
        api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL"),
    ),
}

if __name__ == "__main__":
    print(BASE_DIR)
    print(LLM_CFG)
