FROM sezra-python-service-base

WORKDIR /app

COPY services/level-1-enricher-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/level-1-enricher-service/main.py .

CMD ["python", "main.py"]
