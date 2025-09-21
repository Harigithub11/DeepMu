# Stage 1: Build
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install --user -r requirements.txt

# Stage 2: Production
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH="/root/.local/bin:$PATH"
RUN apt-get update && \
    apt-get install -y --no-install-recommends libgomp1 && \
    rm -rf /var/lib/apt/lists/* && \
    adduser --disabled-password --gecos '' deepmu

USER deepmu
CMD ["gunicorn", "main:app", "--config", "gunicorn_conf.py"]