FROM python:3.11-slim-bookworm

WORKDIR /app

COPY services/face_processing/requirements.txt .
# COPY requirements.txt .
RUN apt-get update && apt-get install -y --no-install-recommends \
        libglib2.0-0 \
        build-essential \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y --auto-remove build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY services/face_processing/app ./app

# Pre-download InsightFace buffalo_l model at build time so the container
# works without internet access at runtime.
RUN python -c "from insightface.app import FaceAnalysis; fa = FaceAnalysis(name='buffalo_l', root='/app/models', providers=['CPUExecutionProvider']); fa.prepare(ctx_id=0, det_size=(640, 640)); print('InsightFace buffalo_l model download complete.')"

EXPOSE 8002

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002", "--workers", "1"]
