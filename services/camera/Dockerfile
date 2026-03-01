FROM python:3.11-slim

# Install system dependencies for RealSense
RUN set -eux; \
    for f in /etc/apt/sources.list /etc/apt/sources.list.d/*.list; do \
        if [ -f "$f" ]; then sed -i 's|http://deb.debian.org/|https://deb.debian.org/|g' "$f"; fi; \
    done; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        apt-transport-https \
        libusb-1.0-0 \
        libgl1 \
        libglx-mesa0 \
        libglib2.0-0; \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]
