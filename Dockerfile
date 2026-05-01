FROM python:3.11-slim

WORKDIR /app

# --- OS packages --------------------------------------------------
RUN apt-get update \
 && apt-get install -y curl \
 && rm -rf /var/lib/apt/lists/*

# --- Python deps --------------------------------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Application code --------------------------------------------
COPY . .

EXPOSE 8501

CMD streamlit run ephemeral_app.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false \
    --server.maxUploadSize="${MAX_UPLOAD_MB:-50}" \
    --browser.serverAddress=0.0.0.0 \
    --browser.serverPort=8501 \
    --browser.gatherUsageStats=false
