import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

# List available models
print("Available Gemini models:")
for model in genai.list_models():
    print(f"  - {model.name}")