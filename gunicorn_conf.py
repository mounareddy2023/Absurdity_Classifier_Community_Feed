# Gunicorn config variables
loglevel = "error"
errorlog = "-"  # stderr
# accesslog = "-"  # stdout
worker_tmp_dir = "/dev/shm"
graceful_timeout = 120
timeout = 120
keepalive = 5
workers = 2
bind = '0.0.0.0:5000'
