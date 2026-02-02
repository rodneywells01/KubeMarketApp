FROM python:3.11-slim

WORKDIR /app

# Install pipenv
RUN pip install --upgrade pip && pip install pipenv

# Copy dependency files
COPY Pipfile Pipfile.lock* ./

# Install dependencies from Pipfile
RUN pipenv install --system --deploy --ignore-pipfile

# Copy application code
COPY . .

ENV FLASK_APP=main.py
ENV FLASK_RUN_HOST=0.0.0.0

EXPOSE 5000

CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]