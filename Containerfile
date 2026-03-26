FROM registry.access.redhat.com/ubi9/python-312:latest

USER 0

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY manager_alert/ manager_alert/

RUN mkdir -p /app/data

VOLUME /app/data

CMD ["python", "-m", "manager_alert", "serve"]
