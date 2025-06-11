FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --verbose -r requirements.txt

COPY . .

# Add logging and error handling
CMD ["python", "-u", "src/main.py"]
