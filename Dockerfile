# ------------------------------------------------------------
# Base image
# ------------------------------------------------------------
FROM python:3.11-slim

# Faster, cleaner Python
ENV PYTHONDONTWRITEBYTECODE=1  \
PYTHONUNBUFFERED=1

# ------------------------------------------------------------
# OS packages (add more if your PDF pipeline needs them)
# ------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential curl git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# ------------------------------------------------------------
# Non-root user + working dirs
# ------------------------------------------------------------
RUN useradd -m -u 1000 appuser

RUN mkdir -p /app 
RUN mkdir -p /secrets 
RUN chmod 755 /secrets
RUN chown -R appuser:appuser /app /secrets
WORKDIR /app


# ------------------------------------------------------------
# Python dependencies (cache-friendly layer order)
# ------------------------------------------------------------
COPY requirements.txt .
RUN python -m pip install --no-cache-dir --upgrade pip 
RUN pip install --no-cache-dir -r requirements.txt

# ------------------------------------------------------------
# App source
# ------------------------------------------------------------
COPY . .

# ------------------------------------------------------------
# Default runtime env (override at `docker run -e ...`)
# ------------------------------------------------------------
ENV STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    APP_TIMEZONE=America/New_York \
    VERTEX_LOCATION=us-east1
# Optionally set a default model:
ENV VERTEX_MODEL_NAME=gemini-2.5-flash


# ------------------------------------------------------------
# Network + user
# ------------------------------------------------------------
EXPOSE 8501
USER appuser

# ------------------------------------------------------------
# Entrypoint
# ------------------------------------------------------------
#CMD ["streamlit", "run", "app.py"]
#CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
CMD ["streamlit", "run", "app.py", "--server.port=8501"]
