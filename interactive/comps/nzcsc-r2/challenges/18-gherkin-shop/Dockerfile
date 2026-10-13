FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir flask gunicorn

COPY . .

RUN groupadd -r user && useradd -r -g user user
USER user

CMD ["gunicorn", "--no-control-socket", "--bind", "0.0.0.0:5000", "app:app"]
