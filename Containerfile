FROM registry.access.redhat.com/ubi9/python-312:latest

USER 0

RUN dnf install -y cronie && dnf clean all

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY manager_alert/ manager_alert/
COPY crontab /etc/cron.d/manager-alert
COPY entrypoint.sh .

RUN chmod 0644 /etc/cron.d/manager-alert && \
    crontab /etc/cron.d/manager-alert && \
    chmod +x entrypoint.sh && \
    mkdir -p /app/data

VOLUME /app/data

ENTRYPOINT ["./entrypoint.sh"]
