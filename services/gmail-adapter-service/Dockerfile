FROM sezra-python-service-base

COPY requirements /requirements
COPY services/gmail-adapter-service/requirements.txt /tmp/service-requirements.txt

RUN pip install --no-cache-dir -r /tmp/service-requirements.txt

COPY services/gmail-adapter-service /app

WORKDIR /app

CMD ["python", "main.py"]
