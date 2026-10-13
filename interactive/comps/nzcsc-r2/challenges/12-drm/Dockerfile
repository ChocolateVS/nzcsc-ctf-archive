FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application lives in /app; the flag sits OUTSIDE it at /flag.txt.
# The intended solve reaches /flag.txt via the legacy endpoint's
# broken path-traversal filter (re.sub only strips one "../").
COPY app.py .
COPY static/ static/
COPY templates/ templates/
COPY tracks/ tracks/
COPY flag.txt /flag.txt

RUN groupadd -r user && useradd -r -g user user
USER user

EXPOSE 5000

CMD ["gunicorn", "--no-control-socket", "--bind", "0.0.0.0:5000", "app:app"]
