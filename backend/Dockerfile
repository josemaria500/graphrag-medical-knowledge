# backend/Dockerfile

FROM python:3.12-slim

WORKDIR /app

# Evita crear archivos .pyc dentro del contenedor
ENV PYTHONDONTWRITEBYTECODE=1

# Hace que los logs de Python salgan directamente en Docker
ENV PYTHONUNBUFFERED=1

# Primero copiamos solo el requirements para aprovechar la caché de Docker
COPY backend/requirements.txt ./backend/requirements.txt

RUN pip install --no-cache-dir -r backend/requirements.txt

# Copiamos lo necesario para la API + el frontend que ahora sirve FastAPI
COPY backend ./backend
COPY config ./config
COPY src ./src
COPY frontend ./frontend

# Aseguramos que Python trate backend y config como paquetes importables
RUN touch backend/__init__.py config/__init__.py

EXPOSE 8000

CMD ["uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8000"]
