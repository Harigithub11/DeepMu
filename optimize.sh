# Memory optimization for FastAPI
sed -i 's/from typing import List/from typing import List, Generator/' main.py
sed -i 's/data = \[/data = (/' src/data_pipeline.py

# Gunicorn production config
cat <<EOL > gunicorn_conf.py
bind = "0.0.0.0:8000"
workers = 3
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120
EOL