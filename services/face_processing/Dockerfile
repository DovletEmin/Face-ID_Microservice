FROM python:3.11-slim-bookworm

WORKDIR /app

COPY services/face_processing/requirements.txt .
# COPY requirements.txt .
RUN apt-get update && apt-get install -y --no-install-recommends \
        libglib2.0-0 \
        libgl1 \
    && pip install --no-cache-dir --prefer-binary -r requirements.txt \
    && rm -rf /var/lib/apt/lists/*

# Disable albumentations version-check network call (avoids SSL timeout on startup)
ENV NO_ALBUMENTATIONS_UPDATE=1

# Pre-build matplotlib font cache so first startup doesn't block for 60s
# RUN python -c "import matplotlib.font_manager; print('Matplotlib font cache built.')"
RUN python -c "import matplotlib.font_manager as fm; fm.findSystemFonts(); print('Matplotlib font cache built.')"


COPY services/face_processing/app ./app

# Copy pre-downloaded InsightFace buffalo_l model (must exist locally before build).
# Download: https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip
# Extract and place the files at: services/face_processing/models/models/buffalo_l/
COPY services/face_processing/models /app/models

EXPOSE 8002

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002", "--workers", "1"]
