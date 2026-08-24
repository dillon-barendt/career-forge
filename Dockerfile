FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CAREER_FORGE_MODE=mock

WORKDIR /app

COPY pyproject.toml uv.lock README.md LICENSE ./
COPY career_ops ./career_ops
COPY benchmark ./benchmark
COPY demo.sh ./

RUN pip install --no-cache-dir uv==0.11.33 \
    && uv sync --locked --no-dev --no-editable \
    && adduser --disabled-password --gecos "" --uid 10001 careerforge \
    && chown -R careerforge:careerforge /app

ENV PATH="/app/.venv/bin:$PATH"

USER careerforge

CMD ["./demo.sh"]
