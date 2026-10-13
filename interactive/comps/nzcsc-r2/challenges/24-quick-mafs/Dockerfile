FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends socat && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir pycryptodome
WORKDIR /app
COPY chall.py /app/chall.py
RUN mkdir -p /src && echo 'NZCSC{REPLACE_ME_quick-mafs}' > /src/flag.txt
RUN useradd -m -u 10001 chal
USER chal
EXPOSE 1337
CMD ["socat","-T120","TCP-LISTEN:1337,reuseaddr,fork","EXEC:python3 -u /app/chall.py,stderr"]
