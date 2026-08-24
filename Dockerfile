FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY career_ops ./career_ops
COPY benchmark ./benchmark
COPY demo.sh ./

RUN pip install --no-cache-dir . \
    && adduser --disabled-password --gecos "" --uid 10001 careerforge \
    && chown -R careerforge:careerforge /app

USER careerforge

CMD ["./demo.sh"]
