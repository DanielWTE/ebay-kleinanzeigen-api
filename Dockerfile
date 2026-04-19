# Use Playwright's official Python image — ships with matching
# Chromium + all system deps pre-installed, avoiding the
# `playwright install-deps` package-name drift against Ubuntu archives.
FROM mcr.microsoft.com/playwright/python:v1.54.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
