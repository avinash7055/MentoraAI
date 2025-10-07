import os, openai

class LLMService:
    def __init__(self):
        openai.api_key = os.getenv("OPENAI_API_KEY")

    def generate_text(self, prompt: str):
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are a UPSC tutor."},
                      {"role": "user", "content": prompt}],
            max_tokens=400
        )
        return completion.choices[0].message["content"].strip()
