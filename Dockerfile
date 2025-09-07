# Usa Python 3.13 slim
FROM python:3.13-slim

# Evitar preguntas de instalación
ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    ffmpeg \
    wget \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Crear carpeta de la app
WORKDIR /app

# Copiar dependencias
COPY requerimientos.txt .

# Instalar librerías de Python
RUN pip install --no-cache-dir -r requerimientos.txt

# Copiar el resto del proyecto
COPY . .

# Exponer puerto que usa Django (por default 8000)
EXPOSE 8000

# Comando para correr la app
CMD ["gunicorn", "YutuMusic.wsgi:application", "--bind", "0.0.0.0:8000", "--timeout", "120"]
