FROM python:3.11-slim-bullseye

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install flask gunicorn

COPY . .

CMD gunicorn -w 1 -b :8080 --access-logfile - --error-logfile - main:app & python main.py
