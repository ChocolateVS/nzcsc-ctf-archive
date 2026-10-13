# TCP / "nc" challenge (a service you connect to with `nc host port`). service.py
# handles one connection per client on port 1337 (matches `port: 1337`). The generator
# publishes it on the host at `tcp_port` so players use: nc <server-ip> <tcp_port>.
FROM python:3.12-slim
WORKDIR /app
COPY service.py .
RUN useradd -m -u 10001 chal
USER chal
EXPOSE 1337
CMD ["python", "service.py"]
