import openai
from langfuse.openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()   
openai_api_key = os.getenv("OPENAI_API_KEY")
openai_model = os.getenv("OPENAI_MODEL")

class LLMConfig:
    def __init__(self, model_name: str):
        self.client = OpenAI()
        self.model_name = model_name

    def get_model_name(self):
        return self.model_name

    def get_client(self):
        return self.client
    
    def get_llm_response(self, prompt: str):
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.choices[0].message.content
 
if __name__ == "__main__":
    llm_config = LLMConfig(os.getenv("OPENAI_MODEL"))
    print(llm_config.get_llm_response("Hello, how are you?")) 
