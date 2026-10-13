# Simple HTTP-API challenge. Copy this folder to comps/<comp>/challenges/<nn-slug>/,
# drop your app in, edit challenge.yml. The FLAG is injected at runtime via env
# (set in flags.env) so the real flag never lives in the image or git.
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY root.json .
# Run as an unprivileged user (defence in depth; the compose file also drops all caps).
RUN useradd -m -u 10001 chal
USER chal
EXPOSE 5000
CMD ["python", "app.py"]
