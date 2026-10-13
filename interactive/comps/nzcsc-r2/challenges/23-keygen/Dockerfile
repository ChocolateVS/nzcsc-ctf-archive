FROM ubuntu:24.04
RUN apt-get update && apt-get install -y --no-install-recommends socat libc6 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY keygen /app/keygen
RUN chmod +x keygen && useradd -m -u 10001 chal
USER chal
EXPOSE 1337
CMD ["socat","-T120","TCP-LISTEN:1337,reuseaddr,fork","EXEC:./keygen,stderr"]
