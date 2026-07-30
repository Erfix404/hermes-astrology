FROM python:3.13-slim

WORKDIR /app

COPY . .

# Test
RUN python -m unittest tests.test_engine -v

# CLI smoke test
RUN python scripts/astro_cli.py --summary 2>&1 | head -5

EXPOSE 8000
CMD ["uvicorn", "scripts.api:app", "--host", "0.0.0.0", "--port", "8000"]
