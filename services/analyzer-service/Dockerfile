FROM sezra-python-service-base

COPY requirements /requirements
COPY services/analyzer-service/requirements.txt /tmp/service-requirements.txt

RUN pip install --no-cache-dir -r /tmp/service-requirements.txt
RUN pip install --no-cache-dir -r /requirements/dev.txt

COPY services/analyzer-service /app

CMD ["python", "main.py"]