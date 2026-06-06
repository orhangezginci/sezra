FROM sezra-python-service-base

COPY requirements /requirements
COPY services/api-service/requirements.txt /tmp/service-requirements.txt
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r /tmp/service-requirements.txt

COPY services/api-service /app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]