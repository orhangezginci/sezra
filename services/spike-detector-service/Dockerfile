FROM sezra-python-service-base

COPY requirements /requirements
COPY services/spike-detector-service/requirements.txt /tmp/service-requirements.txt

RUN pip install --no-cache-dir -r /tmp/service-requirements.txt

COPY services/spike-detector-service /app

CMD ["python", "main.py"]