# Get the env at the very top before any
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY") 
CHUNK_SIZE = os.getenv("CHUNK_SIZE")
CHUNK_OVERLAP = os.getenv("CHUNK_OVERLAP")

#get the logger done also at the top.
from utils.logger import init_logger
logger = init_logger(__name__)


import os, pathlib, tempfile, json, tqdm
from qdrant_client import QdrantClient, models
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader

EMBED_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
assert EMBED_MODEL is not None, "Embedding model is not loaded!"

#---- First load them from .env-----------------------------------------
COLLECTION = "pdf_chunks"
qclient = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

def create_chunks(text, chunk_size, chunk_overlap):
    splitter = RecursiveCharacterTextSplitter(chunk_size, chunk_overlap)
    return splitter.split_text(text)

def check_qdrant_collection():
    if COLLECTION not in [c.name for c in qclient.get_collections().collections]:
        logger.warning(f"Collection {COLLECTION} does not exist in Qdrant")
        return False
    return True



def reset_qdrant_collection():
    if COLLECTION in [c.name for c in qclient.get_collections().collections]:
        qclient.delete_collection(COLLECTION)
    logger.warning(f"Collection {COLLECTION} has been deleted from Qdrant")
    return True



def load_pdf_to_qdrant(file) -> bool:
    reader = PdfReader(file)
    full_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    chunk_size=CHUNK_SIZE
    chunk_overlap=CHUNK_OVERLAP
    docs = create_chunks(full_text,chunk_size,chunk_overlap)


    embeddings = EMBED_MODEL.encode(docs, show_progress_bar=True)
    vectors = [
        models.PointStruct(id=i, vector=vec, payload={"text": t})
        for i, (vec, t) in enumerate(zip(embeddings, docs))
    ]

    if COLLECTION not in [c.name for c in qclient.get_collections().collections]:
        qclient.recreate_collection(
            COLLECTION,
            vectors_config=models.VectorParams(size=len(embeddings[0]), distance=models.Distance.COSINE),
        )
    qclient.upsert(collection_name=COLLECTION, points=vectors)
    return True




def similarity_search(query: str, k: int = 5) -> list:
    if query is None or query.strip() == "":
        logger.error("Query is empty")
        return [] 
    
    if qclient is None:
        logger.error("Qdrant client is not initialized")
        return []
    
    if COLLECTION not in [c.name for c in qclient.get_collections().collections]:
        logger.error(f"Collection {COLLECTION} does not exist in Qdrant")
        return []   
    
       
    EMBED_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    if EMBED_MODEL is None:
        assert EMBED_MODEL is not None, "Embedding model is not loaded!"
        logger.error("Embedding model not loaded")
        return None
    else:
        qvec = EMBED_MODEL.encode(query).tolist()
        hits = qclient.search(COLLECTION, qvec, limit=k)
        return [h.payload["text"] for h in hits]
    