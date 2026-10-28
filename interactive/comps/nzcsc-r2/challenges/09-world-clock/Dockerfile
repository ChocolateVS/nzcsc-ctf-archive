FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN groupadd -r user && useradd -r -g user user
USER user

CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
