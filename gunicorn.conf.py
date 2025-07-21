# Gunicorn configuration for better performance

# Server socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker processes
workers = 2  # Reduced from default to avoid resource contention
worker_class = "sync"
worker_connections = 1000
timeout = 60  # Increased from 30 to handle slow operations
keepalive = 2

# Restart workers after this many requests, to prevent memory leaks
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "catcare"

# Server mechanics
daemon = False
pidfile = "/tmp/catcare.pid"
user = None
group = None
tmp_upload_dir = None

# SSL (if needed)
keyfile = None
certfile = None