FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends socat && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir pycryptodome
WORKDIR /app
COPY server.py flag.txt ./
RUN useradd -m -u 10001 chal
USER chal
EXPOSE 1337
# interactive stdin/stdout program exposed over TCP (nc) via socat
CMD ["socat","-T120","TCP-LISTEN:1337,reuseaddr,fork","EXEC:python3 -u server.py,stderr"]
