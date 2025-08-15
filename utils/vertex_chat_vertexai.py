# vertex_chat_vertexai.py
# Get the env at the very top before any
import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

#get the logger done also at the top.
from utils.logger import init_logger
logger = init_logger(__name__)

# Vertex AI (Gemini on Vertex)
import vertexai
from vertexai.generative_models import GenerativeModel, Content, Part, GenerationConfig


# --- Helpers -----------------------------------------------------------------
def _to_vertex_history(messages: list[dict]) -> list[Content]:
    """
    Convert [{'role': 'user'|'assistant', 'content': '...'}] -> Vertex Content[]
    Skips the final user message (the one we will send) — caller should slice.
    """
    #role_map = {"user": Role.USER, "assistant": Role.MODEL}
    role_map = {"user": "user", "assistant": "model"}

    history: list[Content] = []
    for m in messages:
        role = role_map.get(m.get("role", "").lower())
        text = (m.get("content") or "").strip()
        if not role or not text:
            continue
        history.append(Content(role=role, parts=[Part.from_text(text)]))
    return history


# --- Public API (same signatures) --------------------------------------------
def init_chat():
    """
    Initialize Vertex AI and return a ChatSession.
    Env vars expected:
      - GOOGLE_CLOUD_PROJECT (required)
      - VERTEX_LOCATION (optional, default 'us-central1')
      - GOOGLE_APPLICATION_CREDENTIALS (path to SA key) OR use 'gcloud auth application-default login'
    """
    project = os.getenv("GOOGLE_CLOUD_PROJECT_ID") or os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT") 
    location = os.getenv("VERTEX_LOCATION", "us-east1")

    if not project:
        raise ValueError(
            "Please set the GOOGLE_CLOUD_PROJECT environment variable for Vertex AI."
        )

    # Initialize Vertex AI
    vertexai.init(project=project, location=location)

    # Choose a Gemini model available on Vertex; adjust if you prefer Pro
    # See: https://cloud.google.com/vertex-ai/generative-ai/docs/learn/models
    model = GenerativeModel(model_name=os.getenv("VERTEX_MODEL_NAME", "gemini-2.5-flash-lite")  )

    # Start an empty chat (we'll add history per-request in chat())
    chat_session = model.start_chat(response_validation=True)  
    return chat_session


def chat(
    my_gemini,  # ChatSession from init_chat()
    system_prompt: str,
    messages: list[dict],
    max_output_tokens: int = 512,
    temperature: float = 0.8,
) -> str:
    """
    Send a message using Vertex AI chat.
    - Builds a system instruction and prior history from `messages[:-1]`
    - Sends the final user message `messages[-1]`
    """
    if not my_gemini:
        logger.error("chat:my_gemini is not initialized. Please call init_chat() first.")
        return None

    if not system_prompt:
        logger.error("chat:System prompt cannot be empty.")
        return None

    if not messages or not isinstance(messages, list):
        logger.error("chat:Messages must be a non-empty list.")
        return None

    # Extract the last user message
    user_message = messages[-1].get("content", "").strip()
    if not user_message:
        logger.warning("User message is empty.")
        return None


    # Rebuild a model with system instruction (Vertex applies system at model-level)
    try:
        model_with_system = GenerativeModel(
            model_name = os.getenv("VERTEX_MODEL_NAME", "gemini-2.5-flash-lite"),
            system_instruction = system_prompt,
        )
    except Exception as e:
        logger.exception(f"Failed to prepare model with system prompt: {e}")
        return None

    # Convert prior history (excluding the last user message)
    prior_history = _to_vertex_history(messages[:-1])

    # Create a fresh chat session including history for this turn
    chat_with_history = model_with_system.start_chat(history=prior_history)


    gen_cfg = GenerationConfig(
        temperature=temperature,
        max_output_tokens=max_output_tokens,
    )

    logger.info(
        "chat:Sending message to Vertex AI Gemini with system+history. "
        f"history_turns={len(prior_history)}, max_tokens={max_output_tokens}, temp={temperature}"
    )

    try:
        response = chat_with_history.send_message(
            Part.from_text(user_message),
            generation_config=gen_cfg,
        )
        return (response.text.strip() if response and hasattr(response, "text") else "")
    except Exception as e:
        logger.exception(f"Vertex AI chat send_message failed: {e}")
        return None
