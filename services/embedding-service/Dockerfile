FROM sezra-python-service-base

COPY requirements /requirements
COPY services/embedding-service/requirements.txt /tmp/service-requirements.txt

RUN pip install --no-cache-dir -r /tmp/service-requirements.txt

COPY services/embedding-service /app

CMD ["python", "main.py"]