# Etapa 1: dependencias en un venv
FROM python:3.12-slim AS build

WORKDIR /app

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Etapa 2: tests unitarios
# Si un test falla, el build entero falla antes de llegar a Build and Push en Jenkins
FROM build AS test

COPY app ./app
COPY tests ./tests

RUN python -m unittest discover -s tests -t . -v

# Etapa 3: runtime
FROM python:3.12-slim

WORKDIR /app

RUN useradd --create-home --uid 1001 appuser

COPY --from=build /opt/venv /opt/venv
COPY app ./app

ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
