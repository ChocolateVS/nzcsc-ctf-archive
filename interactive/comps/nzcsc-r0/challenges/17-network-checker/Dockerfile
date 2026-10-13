# Simple HTTP-API challenge. Copy this folder to comps/<comp>/challenges/<nn-slug>/,
# drop your app in, edit challenge.yml. The FLAG is injected at runtime via env
# (set in flags.env) so the real flag never lives in the image or git.
FROM python:3.12-slim
WORKDIR /app
# The "network checker" shells out to ping. Docker sets net.ipv4.ping_group_range
# so unprivileged (SOCK_DGRAM) ping works even with all caps dropped.
RUN apt-get update \
    && apt-get install -y --no-install-recommends iputils-ping \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
# Run as an unprivileged user (defence in depth; the compose file also drops all caps).
RUN useradd -m -u 10001 chal
# Provision an empty, chal-writable flag file. The real flag is written into it
# at runtime by app.py from the FLAG env var, so it never lives in the image.
RUN touch /app/flag.txt && chown chal:chal /app/flag.txt
USER chal
EXPOSE 5000
CMD ["python", "app.py"]
