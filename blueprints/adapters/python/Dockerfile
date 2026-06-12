FROM sezra-python-service-base

COPY requirements /requirements
COPY blueprints/adapters/python/requirements.txt /tmp/service-requirements.txt

RUN pip install --no-cache-dir -r /tmp/service-requirements.txt

COPY blueprints/adapters/python /app

WORKDIR /app

CMD ["python", "main.py"]