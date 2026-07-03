FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-di -r requirements.txt

COPY . .

RUN useradd -m botuser && chown -R botuser /app
USER botuser

CMD ["python", "bot.py"]
