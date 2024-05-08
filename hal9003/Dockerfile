FROM python:3.11-alpine

WORKDIR /bot
COPY . .

RUN pip install -r requirements.txt

ENV PYTHONUNBUFFERED=1

EXPOSE 3334

ENTRYPOINT [ "sh", "./entry.sh" ]