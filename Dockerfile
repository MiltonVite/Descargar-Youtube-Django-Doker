# Usa Python 3.13 slim como base
FROM python:3.13-slim

# Evitar preguntas de instalación
ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependencias del sistema necesarias
RUN apt-get update && apt-get install -y \
    ffmpeg \
    wget \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Crear carpeta de descargas
RUN mkdir -p /app/downloads

# Establecer directorio de trabajo
WORKDIR /app

# Copiar requerimientos
COPY requerimientos.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requerimientos.txt

# Copiar el resto del proyecto
COPY . .

# Copiar cookies a una ruta fija dentro del contenedor
RUN cp DescargarMusicaVideos/www.youtube.com_cookies.txt /app/cookies.txt

# Exponer el puerto que usa Django (8000 por defecto)
EXPOSE 8000

# Ejecutar la app con Gunicorn
# - 3 workers para manejar múltiples peticiones
# - 2 threads por worker
# - timeout de 120s para operaciones largas (ej. yt-dlp)
CMD ["gunicorn", "YutuMusic.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--threads", "2", "--timeout", "120"]
