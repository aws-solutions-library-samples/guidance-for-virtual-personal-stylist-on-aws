
FROM python:3.11-slim-bullseye

ENV HOST=0.0.0.0
 
ENV LISTEN_PORT 8501

RUN apt-get clean && apt-get update

COPY requirements.txt /app/requirements.txt
 
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

WORKDIR /app

COPY demo_app/stylistapp.py .

EXPOSE 8501

CMD ["streamlit", "run", "stylistapp.py", "--server.port", "8501"]

