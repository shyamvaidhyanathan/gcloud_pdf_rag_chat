# PDF RAG Chat with Google LLMs

This project is an experimental Retrieval-Augmented Generation (RAG) chat app that lets you upload a PDF and then chat interactively with its content.  
<br><br>
It has been built with :
- **Vector Store:** Qdrant (free tier on GCP)    <br>
- **Short-term memory:** Redis  ( https://cloud.redis.io/ ) <br>  
- **Long-term memory:** Firestore (Google Cloud free tier)  <br>
- **Language model:** Choices between Gemini on Google AI, Gemini on Vertex AI and Gemma. <br> 
- **Frontend:** Streamlit  <br>
- **Deployment:** Docker image build and deployed using Google Cloud Run  <br>

---

## Features
- Upload PDF, vectorize & index text chunks  
- Chat UI that queries vectors + remembers recent & long-term context  
- Summarizes conversations older than 2 minutes and stores them into Firestore  
- Backend LLM can be changed.(Multiple choices)  

---
<br>
<br>
<br>

## Getting Started

### Prerequisites

- Python 3.10+  
- Docker (optional, for containerized runs locally to test)  
- Google Cloud Project with:  
  - Firestore enabled  
  - Qdrant Cloud cluster (free tier)  
  - Redis.io (free tier)  
  - Vertex AI enabled
  - GoogleAI enabled   
<br>
<br>
<br>

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
```bash

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
```

5. Run Locally & Validate the Functionality
streamlit run app.py

6. Build and run within Docker Desktop locally
```bash
docker build -t pdf-rag-gcloud .
docker run --env-file .env -p 8501:8501 pdf-rag-gcloud
```
<br>
<br>
<br>

### Build the Docker Image 

Option 1. Locally build and then push to artifactory 
#### Build and tag your Docker image:
```bash
docker build -t us-east1-docker.pkg.dev/<GCP_PROJECT_ID>/rag-chat-repo/pdf-rag-gcloud:latest .
```

#### Push to Artifactory Registry
```bash
docker push us-east1-docker.pkg.dev/<GCP_PROJECT_ID>/rag-chat-repo/pdf-rag-gcloud:latest
```
<br>
Option 2. Submit to gcloud to the build 
<br>

```bash 
gcloud builds submit --tag us-east1-docker.pkg.dev/learntododeploycloudrun/rag-app-repo/rag-app:latest
```
<br>
<br>
<br>
<br>
<br>
### Deploy to Cloud Run 

#### Option 1. Using Beta version you can use .env file.
```bash 
gcloud beta run deploy rag-chat-app   --image $IMAGE   --region us-east1   --allow-unauthenticated   --port 8501   --memory 2Gi   --cpu 1   --concurrency 80   --service-account <serviceaccount>  --env-vars-file .env
```
<br>
<br>
<br>

#### Option 2. Without .env but specifying each env variable and setting secrets explicitely

```bash 
echo -n "<redis_URL>" | gcloud secrets create redis-url --data-file=-
echo -m "<QdrantAPI Key>" | gcloud secrets create qdrant-api-key --data-file=-
IMAGE="us-east1-docker.pkg.dev/learntododeploycloudrun/rag-app-repo/rag-app:latest"
gcloud run deploy rag-chat-app   --image $IMAGE   --region us-east1   --allow-unauthenticated   --port 8501   --memory 2Gi   --cpu 1   --concurrency 80   --service-account <service account>   --set-env-vars GOOGLE_CLOUD_PROJECT="<GCP Project>,VERTEX_LOCATION="us-east1",VERTEX_MODEL_NAME="gemini-2.5-flash",APP_TIMEZONE="America/New_York",QDRANT_URL="<Qdrant URL>"   --set-secrets REDIS_URL=redis-url:latest --set-secrets QDRANT_API_KEY=qdrant-api-key:latest
```
<br>
