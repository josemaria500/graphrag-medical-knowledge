# frontend/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Evitar archivos .pyc y asegurar logs en tiempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY frontend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY frontend .

EXPOSE 8501

# Configuración de Streamlit para que corra en modo servidor
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]