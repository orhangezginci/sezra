FROM sezra-python-service-base

COPY requirements /requirements
COPY services/event-store-service/requirements.txt /tmp/service-requirements.txt

RUN pip install --no-cache-dir -r /tmp/service-requirements.txt
COPY contracts /contracts
COPY services/event-store-service /app

CMD ["python", "main.py"]