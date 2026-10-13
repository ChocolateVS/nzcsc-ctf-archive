FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir flask gunicorn

COPY . .

RUN groupadd -r user && useradd -r -g user user
USER user

EXPOSE 5000

# Single worker: game state is kept in-process keyed by the session cookie.
CMD ["gunicorn", "--no-control-socket", "--workers", "1", "--bind", "0.0.0.0:5000", "app:app"]
