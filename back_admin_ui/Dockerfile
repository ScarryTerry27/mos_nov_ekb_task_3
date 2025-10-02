FROM python:3.11-slim

# В вашем Dockerfile backend
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg \
 && rm -rf /var/lib/apt/lists/*

RUN mkdir /backend

WORKDIR /backend

COPY requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONPATH=/backend

COPY ../backend_admin_ui /backend

EXPOSE 8000