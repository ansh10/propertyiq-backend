import os

bind = f"0.0.0.0:{os.environ.get('PORT', 10000)}"
workers = 1  # Single worker to avoid memory issues on free tier
worker_class = "sync"
timeout = 120  # 2 minute timeout
keepalive = 5
accesslog = "-"
errorlog = "-"
loglevel = "info"