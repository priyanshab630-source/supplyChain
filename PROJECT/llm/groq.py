from dotenv import load_dotenv
import os
from langchain_groq import ChatGroq

load_dotenv()

def get_groq_model():

    api_key = os.getenv("GROQ_API_KEY")

    print(api_key)      # temporary debugging

    return ChatGroq(
        model="openai/gpt-oss-120b",
        api_key=api_key,
    )