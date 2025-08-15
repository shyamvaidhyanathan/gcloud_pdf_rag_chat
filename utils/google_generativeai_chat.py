import google.generativeai as geminiai
import os
from dotenv import load_dotenv,find_dotenv
load_dotenv(find_dotenv())

from utils.logger import init_logger
logger = init_logger(__name__)


def init_chat():
    try:
        geminiai.configure(api_key=os.getenv("GOOGLE_GEMINI_API_KEY")) 
    except AttributeError:
        raise ValueError("Please set the GOOGLE_GEMINI_API_KEY environment variable.")
        exit()
    model = geminiai.GenerativeModel(model_name="gemini-2.0-flash")     
    my_gemini= model.start_chat()
    return my_gemini


def chat(my_gemini, system_prompt: str, messages: list[dict], max_output_tokens=512, temperature=0.7) -> str:
    if not my_gemini:
        logger.error("chat:my_gemini is not initialized. Please call init_chat() first.")
        return None
    
    if not system_prompt:
        logger.error("chat:System prompt cannot be empty.")
        return None
    
    if not messages or not isinstance(messages, list):
        logger.error("chat:Messages must be a non-empty list.")
        return None

    context = system_prompt + "\n" + "\n".join(f"{m['role'].capitalize()}: {m['content']}" for m in messages[:-1])
    user_message = messages[-1]["content"]

    if not user_message:
        logger.warning("User message is empty.")
        return None

    content=context + "\nUser: " + user_message + "\nAssistant:"

    logger.info(f"chat:Sending message to Gemini chat model with content: {content}")

    response = my_gemini.send_message(content=content,)        
    return (response.text.strip() if response and response.text else "")    