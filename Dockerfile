FROM python:3.11-slim

WORKDIR /app

# --- OS packages --------------------------------------------------
RUN apt-get update \
 && apt-get install -y build-essential curl \
 && rm -rf /var/lib/apt/lists/*

# --- Python deps --------------------------------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Application code --------------------------------------------
COPY . .
# --- Streamlit config --------------------------------------------
RUN mkdir -p .streamlit && \
    { cat <<'EOF_SERVER'
[server]
headless = true
enableCORS = false
enableXsrfProtection = false
port = 8501
address = "0.0.0.0"

[browser]
serverAddress     = "0.0.0.0"
serverPort        = 8501
gatherUsageStats  = false

EOF_SERVER
    cat .streamlit/config.toml; } > .streamlit/config.toml.merged && \
    mv .streamlit/config.toml.merged .streamlit/config.toml

EXPOSE 8501

CMD ["streamlit", "run", "ephemeral_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
