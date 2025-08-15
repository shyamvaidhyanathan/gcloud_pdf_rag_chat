## Get the env at the very top before any
import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
REDIS_URL = os.getenv("REDIS_URL")

import redis
redis_client = redis.Redis.from_url(REDIS_URL)

#get the logger done also at the top.
from utils.logger import init_logger
logger = init_logger(__name__)

import streamlit as st, uuid, json, importlib
from utils.vector_store import load_pdf_to_qdrant, similarity_search, reset_qdrant_collection
from utils.memory import remember_short, recall_short, store_long, fetch_summary

import json
from utils.timestamp import now_ts, format_ts


# -----------------------------------------------------------------------------
# Page config
# -----------------------------------------------------------------------------
st.set_page_config(page_title="RAG Chat with PDF", layout="wide")

# -----------------------------------------------------------------------------
# Sidebar: Model provider + model selection
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Sidebar: Upload & vectorize
# -----------------------------------------------------------------------------
st.sidebar.header("Upload your PDF as knowledge base")
uploaded = st.sidebar.file_uploader("Select PDF", type=["pdf"])
if uploaded:
    if st.sidebar.button("Vectorize & Index"):
        with st.spinner("Vectorizing… this may take a moment"):
            reset_qdrant_collection()
            st.toast('Qdrant has been reset', icon='🧹')
            load_pdf_to_qdrant(uploaded)
            st.sidebar.success("✅ Vector store ready!")



st.sidebar.header("Select Model")
provider = st.sidebar.selectbox(
    "Choose API provider",
    options=["GoogleAI", "VertexAI"],
    index=0,
    help="Switch between Google Generative AI (direct) and Vertex AI (Gemini on Vertex)."
)

MODEL_OPTIONS = {
    "GoogleAI": [
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemma-3n-e2b-it",
        "gemma-3n-e4b-it",
        "gemma-3-1b-it",
        "gemma-3-4b-it",
    ],
    "VertexAI": [
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
    ],
}


default_model_index = 0
model_name = st.sidebar.selectbox(
    "Model name",
    options=MODEL_OPTIONS[provider],
    index=default_model_index,
    help="Pick a Gemini model variant for the selected provider."
)

# Map provider -> python module path
MODULE_BY_PROVIDER = {
    "GoogleAI": "utils.google_generativeai_chat",
    "VertexAI": "utils.vertex_chat_vertexai",
}

def _init_backend(selected_provider: str, selected_model: str):
    # Set env variables so backend modules can read the chosen model
    if selected_provider == "VertexAI":
        os.environ["VERTEX_MODEL_NAME"] = selected_model
    elif selected_provider == "GoogleAI":
        # Set multiple names for compatibility with common patterns
        os.environ["GOOGLEAI_MODEL_NAME"] = selected_model
        os.environ["GEMINI_MODEL_NAME"] = selected_model
    module_name = MODULE_BY_PROVIDER[selected_provider]
    mod = importlib.import_module(module_name)
    session = mod.init_chat()
    return mod, session

# Initialize / switch backend when provider or model changes
provider_changed = st.session_state.get("provider") != provider
model_changed = st.session_state.get("model_name") != model_name

if "provider" not in st.session_state or "model_name" not in st.session_state or provider_changed or model_changed:
    st.session_state["provider"] = provider
    st.session_state["model_name"] = model_name
    try:
        chat_module, my_gemini = _init_backend(provider, model_name)
        st.session_state["chat_module"] = chat_module
        st.session_state["my_gemini"] = my_gemini
        st.toast(f"Using {provider} • {model_name}", icon="🤖")
    except Exception as e:
        st.session_state["chat_module"] = None
        st.session_state["my_gemini"] = None
        st.error(f"Failed to initialize {provider} ({model_name}): {e}")

# Convenience handles
chat_module = st.session_state.get("chat_module")
my_gemini = st.session_state.get("my_gemini")
my_chat = getattr(chat_module, "chat", None) if chat_module else None

# Optional button to reinitialize the session for the selected provider+model
if st.sidebar.button("Reinitialize Model Session"):
    try:
        chat_module, my_gemini = _init_backend(st.session_state["provider"], st.session_state["model_name"])
        st.session_state["chat_module"] = chat_module
        st.session_state["my_gemini"] = my_gemini
        st.toast("Model session reinitialized", icon="🔄")
    except Exception as e:
        st.error(f"Failed to reinitialize session: {e}")

st.sidebar.caption(f"Active: **{st.session_state.get('provider','–')} • {st.session_state.get('model_name','–')}**")


# -----------------------------------------------------------------------------
# Main page: Chat UI
# -----------------------------------------------------------------------------
with st.expander("Open Chat Section", expanded=True):
    st.header("Chat with your document")

    chat_id = st.session_state.setdefault("chat_id", str(uuid.uuid4()))

    if st.button("Reset"):
        reset_qdrant_collection()
        st.toast('Qdrant has been reset', icon='🧹')
        st.session_state.messages = []
        redis_client.flushall()   # clear Redis DB
        redis_client.delete(chat_id)
        st.toast('Redis has been reset', icon='🧹')
        # Reinit the model session for current provider+model
        try:
            chat_module, my_gemini = _init_backend(st.session_state["provider"], st.session_state["model_name"])
            st.session_state["chat_module"] = chat_module
            st.session_state["my_gemini"] = my_gemini
        except Exception as e:
            st.error(f"Failed to reinitialize session: {e}")
        st.rerun()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    user_prompt = st.chat_input("Ask anything about the uploaded PDF…")

    if redis_client is None:
        st.error("Redis client could not be initialized. Please check your REDIS_URL.")
        response = "Error: Redis client initialization failed."
    else:
        if user_prompt:
            if not (my_gemini and my_chat):
                st.error("Model is not initialized. Check the selected provider in the sidebar.")
            else:
                logger.debug(f"user_prompt: {user_prompt}")

                # Debug: print short-term memory
                redis_list = redis_client.lrange(chat_id, 0, -1)
                for li in redis_list:
                    logger.debug(f"Recall short-term memory: {json.loads(li)}")

                recent, older = recall_short(chat_id)

                if older:
                    system_prompt = "You are a helpful assistant..."
                    st.toast('Writing a summary to Firestore ..', icon='🎉')
                    logger.debug(f"Older messages: {older}")
                    store_long(my_gemini, chat_id, older)
                    # free short-term space
                    # (We briefly set redis_client to None to avoid accidental use; re-create below)
                    redis_client = None
                    st.session_state.messages = recent  # keep recent only

                context_snippets = similarity_search(user_prompt)
                summary_cache = fetch_summary(chat_id)
                logger.debug(f"Chat ID: {chat_id}")
                logger.debug(f"Summary Cache: {summary_cache}")

                # Build system prompt with context
                system_prompt = (
                    "You are a helpful assistant that answers only from the document.\n\n"
                    f"Document context:\n• " + "\n• ".join(context_snippets) + "\n\n"
                    f"Conversation summary: {summary_cache}"
                )

                gemini_response = my_chat(
                    my_gemini,
                    system_prompt,
                    recent + [{"role": "user", "content": user_prompt}]
                )

                # Recreate redis client if we nulled it above
                if redis_client is None:
                    redis_client = redis.Redis.from_url(REDIS_URL)

                if redis_client is None:
                    st.error("Redis client could not be initialized. Please check your REDIS_URL.")
                    response = "Error: Redis client initialization failed."
                else:
                    if gemini_response:
                        st.session_state.messages.append({"role": "user", "content": user_prompt, "ts": now_ts()})
                        st.session_state.messages.append({"role": "assistant", "content": gemini_response, "ts": now_ts() })
                        redis_client.expire(chat_id, 1200)

                        remember_short(chat_id, "user", user_prompt, redis_client)
                        remember_short(chat_id, "assistant", gemini_response, redis_client)
                        logger.debug(f"ttl= {redis_client.pttl(chat_id)} ms \n")

                        # Debug: print updated short-term memory
                        redis_list = redis_client.lrange(chat_id, 0, -1)
                        for li in redis_list:
                            logger.debug(f"\n {json.loads(li)}  ")

    # Show chat history in reverse order (latest first)
    for msg in reversed(st.session_state.messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            ts = msg.get("ts")
            if ts:
                st.caption(format_ts(ts))