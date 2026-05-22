FROM sezra-python-service-base

COPY requirements /requirements
COPY services/json-file-adapter/requirements.txt /tmp/service-requirements.txt

RUN pip install --no-cache-dir -r /tmp/service-requirements.txt

COPY services/json-file-adapter /app

CMD ["python", "main.py"]