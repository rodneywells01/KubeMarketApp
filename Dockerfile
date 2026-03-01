FROM python:3.11-slim

WORKDIR /app

# Install pipenv
RUN pip install --upgrade pip && pip install pipenv

# Copy dependency files
COPY Pipfile Pipfile.lock ./

# Install dependencies from Pipfile
RUN pipenv install --system --deploy

# Copy application code
COPY . .

ENV FLASK_APP=main.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV GUNICORN_WORKERS=2
ENV GUNICORN_THREADS=4
ENV GUNICORN_TIMEOUT=60

EXPOSE 5000

CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:5000 --workers ${GUNICORN_WORKERS} --threads ${GUNICORN_THREADS} --timeout ${GUNICORN_TIMEOUT} main:app"]
