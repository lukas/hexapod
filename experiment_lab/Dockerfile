FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml README.md ./
COPY hexapod_lab ./hexapod_lab
RUN pip install --no-cache-dir .
RUN useradd --system --uid 10001 --create-home lab && mkdir -p /data && chown lab:lab /data
USER lab
ENV HEXAPOD_DATA_DIR=/data HEXAPOD_BIND=0.0.0.0
EXPOSE 8767
CMD ["hexapod-lab"]
