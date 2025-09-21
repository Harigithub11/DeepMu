#!/bin/bash

# 1. Create missing __init__.py files
find project -type d -name "__pycache__" -exec rm -rf {} \;
find project -type d | while read DIR; do
    echo "Creating __init__.py in $DIR"
    touch "$DIR/__init__.py"
done

# 2. Add SECRET_KEY to .env.example
echo "SECRET_KEY=your_secure_key" >> .env.example

# 3. Update Dockerfile
cat <<EOL > Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--reload", "--port", "8000"]
EOL

# 4. Update docker-compose.yml
cat <<EOL > docker-compose.yml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env.example
    volumes:
      - .:/app
EOL

# 5. Update README.md
echo "## Setup" > README.md
echo "1. Copy .env.example to .env" >> README.md
echo "2. Run: pip install -r requirements.txt" >> README.md
echo "3. Start: docker-compose up" >> README.md

# 6. Add configuration loading
cat <<EOL > project/config/__init__.py
from dotenv import load_dotenv
import os

load_dotenv()
EOL

echo "✅ Setup complete. Run 'docker-compose up' to test!"