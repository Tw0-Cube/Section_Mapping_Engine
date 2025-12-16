import google.generativeai as genai
import os

API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key = API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

def explain_legal_term(term: str) -> str:
    try:
        chat = model.start_chat()
        prompt = f"Explain in 2-3 lines the legal meaning of {term}. Make it simple enough for a common man to understand."
        response = chat.send_message(prompt)
        return response.text
    except Exception as e:
        return f"Error: {e}"