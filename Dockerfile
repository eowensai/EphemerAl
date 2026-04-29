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
# --- Streamlit config --------------------------------------------
RUN mkdir -p .streamlit && \
    printf '%s\n' \
        '[server]' \
        'headless = true' \
        'enableCORS = false' \
        'enableXsrfProtection = false' \
        'maxUploadSize = 50' \
        'port = 8501' \
        'address = "0.0.0.0"' \
        '' \
        '[browser]' \
        'serverAddress     = "0.0.0.0"' \
        'serverPort        = 8501' \
        'gatherUsageStats  = false' \
        '' > .streamlit/config.server.toml && \
    cat .streamlit/config.server.toml .streamlit/config.toml > .streamlit/config.toml.merged && \
    mv .streamlit/config.toml.merged .streamlit/config.toml && \
    rm .streamlit/config.server.toml

EXPOSE 8501

CMD ["streamlit", "run", "ephemeral_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
