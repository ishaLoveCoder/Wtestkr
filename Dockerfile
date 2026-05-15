FROM python:3.11-slim

WORKDIR /app

COPY . /app

RUN apt update && apt install -y gcc python3-dev

RUN pip install --no-cache-dir -r requirements.txt

RUN chmod +x start.sh

EXPOSE 8000

CMD ["bash", "start.sh"]
