FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libvips \
    libgdcm-tools \
    python3-gdcm \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Installing Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY ./src /app/src
WORKDIR /app/src

EXPOSE 8001

HEALTHCHECK CMD curl --fail http://localhost:8001/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]