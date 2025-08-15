
# Get the env at the very top before any
import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID") or os.getenv("GCP_CLOUD_PROJECT")
OLDER = os.getenv("OLDER")  #seconds
REDIS_URL = os.getenv("REDIS_URL")


#get the logger done also at the top.
from utils.logger import init_logger
logger = init_logger(__name__)


import time, json, redis, google.cloud.firestore as fs
from utils.google_generativeai_chat import chat as my_chat

# --- short-term memory (≤5 min) in Redis ---
redis_client = redis.Redis.from_url(REDIS_URL)


# --- long-term memory (> 60 secs, summarized) and stored in GCloud Firestore ---
db = fs.Client(project=GCP_PROJECT_ID) 
if not db:
    raise Exception("Firestore client not initialized. Check GCP_PROJECT_ID.")  
summary_col = db.collection("chat_summaries")
# Retrieve all documents in the collection
docs = summary_col.stream()
for doc in docs:
    logger.debug(f"Document ID: {doc.id}, Data: {doc.to_dict()}")






# Function to extract text from a protobuf response object
# This is used to handle cases where the content is a protobuf object
def extract_text_from_response(response):
    try:
        return "".join(part.text for part in response.candidates[0].content.parts)
    except Exception as e:
        return str(response)



# Function to remember a short-term message in Redis
# It stores the message with a timestamp and role (user/assistant)
def remember_short(chat_id, role, content, redis_client):
    # Extract plain text if content is a protobuf response object
    if hasattr(content, "candidates"):
        content_text = extract_text_from_response(content)
    else:
        content_text = str(content)
        logger.debug(f"chat {chat_id}  | store in Redis| | role {role} | content: {content_text[:50]}...")   

    redis_client.rpush(chat_id, json.dumps({
        "ts": time.time(),
        "role": role,
        "content": content_text
    }))



# Function to recall short-term messages from Redis
# It retrieves messages from the Redis list for the given chat_id
def recall_short(chat_id):
    history = [json.loads(m) for m in redis_client.lrange(chat_id, 0, -1)]
    OLDER = os.getenv("OLDER")  #seconds
    cutoff = time.time() - int(OLDER)               
    recent, older = [m for m in history if m["ts"] >= cutoff], [m for m in history if m["ts"] < cutoff]
    logger.debug(f"chat {chat_id} | recent {recent} | older {older} .")
    return recent, older


def store_long(my_gemini, chat_id, older):
    if not older:
        return

    prompt = "Generate a summary of the conversation between the 'user' and 'assistant'in under 2 sentences \n\n"
    # Compose text to summarize from older messages:
    content = "\n".join(f'{m["role"]}: {m["content"]}' for m in older)
    logger.debug(f"store_long: chat {chat_id} | Len of Order messages = {len(older)} ")
    content = prompt + content
    response = my_gemini.send_message(content=content,)        
    summary_text = response.text.strip() if response else ""
    #Write the summary to Firestore
    summary_col.document(chat_id).set({"last_ts": time.time(), "summary": summary_text})
    logger.debug(f"\n store_long: chat {chat_id} | Summary: {summary_text[:50]} in Firestore.")

    


# Function to fetch the summary for a chat from Firestore
# It retrieves the document for the given chat_id and returns the summary text
def fetch_summary(chat_id):
    doc = summary_col.document(chat_id).get()
    if doc.exists:
        logger.debug(f"Fetched summary for chat {chat_id} \n")
        logger.debug(doc.to_dict()["summary"])
        return doc.to_dict()["summary"]
    else:
        logger.warning(f"fetch_summary: No summary found for chat {chat_id}. Returning empty string.")
        return ""