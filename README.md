# PDF RAG Chat with Google Gemma

This project is a Retrieval-Augmented Generation (RAG) chat app that lets you upload a PDF and then chat interactively with its content.  
It uses:

- **Vector Store:** Qdrant (free tier on GCP)  
- **Short-term memory:** Redis  ( https://cloud.redis.io/ )  
- **Long-term memory:** Firestore (Google Cloud free tier)  
- **Language model:** Google Gemma (Vertex AI managed)  
- **Frontend:** Streamlit  
- **Deployment:** Docker container deployable to Google Cloud Run  

---

## Features

- Upload PDF, vectorize & index text chunks  
- Chat UI that queries vectors + remembers recent & long-term context  
- Summarizes conversations older than 5 minutes for efficiency  
- Pluggable LM backend: Vertex AI Gemma  

---

## Getting Started

### Prerequisites

- Python 3.10+  
- Docker (optional, for containerized runs locally to test)  
- Google Cloud Project with:  
  - Firestore enabled  
  - Qdrant Cloud cluster (free tier)  
  - Redis instance (Redis Cloud- free tier)  
  - Vertex AI enabled   

### Local Setup & Execution

1. Clone the repo and set up local environment and install dependencies using the requirements.txt file:

```bash
git clone https://github.com/yourusername/pdf-rag-chat-gemma.git
cd pdf-rag-chat-gemma
```

2. Create a virtual environment & activate it 

```bash
python -m venv env
source env/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies 
```bash
pip install -r requirements.txt    #this till take some time !!!!! 
```

4. Create a .env file in the root with your secrets:
QDRANT_URL=<your-qdrant-url>
QDRANT_API_KEY=<your-qdrant-api-key>
REDIS_URL=<your-redis-url>           # e.g. rediss://:password@host:port
GCP_PROJECT_ID=<your-gcp-project-id>
GOOGLE_CLOUD_PROJECT_ID=<your-gcp-project-id>
GEMMA_MODEL=<your-google-gemma-model>
GOOGLE_GEMINI_API_KEY=<your-google-ai-key>
VERTEX_MODEL_NAME=<model-from-model-garden-in-vertexai>
OLDER=120        #How many seconds qualifies a chat as older chat.
CHUNK_SIZE=300   #Chunk size during chunking step
CHUNK_OVERLAP=50 #Chunk overlap size.


5. Run Locally & Validate the Functionality
streamlit run app.py

6. Build and run Docker container:
```bash
docker build -t pdf-rag-gcloud .
docker run --env-file .env -p 8501:8501 pdf-rag-gcloud
```

### Deployment to Google Cloud Run

1. Build and tag your Docker image:

docker build -t us-east1-docker.pkg.dev/<GCP_PROJECT_ID>/rag-chat-repo/pdf-rag-gcloud:latest .

2. Push to Artifactory Registry
docker push us-east1-docker.pkg.dev/<GCP_PROJECT_ID>/rag-chat-repo/pdf-rag-gcloud:latest

3. Deploy to Cloud Run
gcloud run deploy pdf-rag-gcloud \
  --image us-east1-docker.pkg.dev/<GCP_PROJECT_ID>/rag-chat-repo/pdf-rag-gcloud:latest \
  --platform managed --region us-east1 --allow-unauthenticated \
  --set-env-vars QDRANT_URL=<...>,QDRANT_API_KEY=<...>,REDIS_URL=<...>,GCP_PROJECT_ID=<...>,GEMMA_MODEL=google/gemma-2b-it



