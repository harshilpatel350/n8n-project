FROM python:3.11-slim

WORKDIR /app

# Copy project into container
COPY .. /app

# Install backend + project requirements
RUN pip install --no-cache-dir -r backend/requirements.txt -r requirements.txt

EXPOSE 8000

CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
