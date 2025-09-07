from django.http import StreamingHttpResponse
from django.shortcuts import render
import os
import yt_dlp
import traceback
import re
import tempfile
import shutil
import uuid


def limpiar_nombre(nombre):
    """Limpia caracteres no válidos para nombres de archivo"""
    return re.sub(r'[^\w\-_\. ]', '_', nombre)


def file_iterator(file_path, temp_dir, chunk_size=8192):
    """Lee el archivo en chunks para enviarlo y borra al final"""
    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(chunk_size):
                yield chunk
    finally:
        # 🔥 Cuando termina, eliminamos el archivo y su carpeta temporal
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception as e:
            print(f"[WARN] No se pudo limpiar: {e}")


def descargar(request):
    try:
        if request.method == 'POST':
            url = request.POST.get('url')
            formato = request.POST.get('formato')

            if not url:
                return render(request, 'descargar.html', {
                    'error': 'Por favor, ingresa una URL válida.'
                })

            # 📂 Carpeta temporal única por descarga
            temp_dir = tempfile.mkdtemp()
            outtmpl = os.path.join(temp_dir, "%(title)s.%(ext)s")

            ffmpeg_path = "/usr/bin/ffmpeg"  # Ajusta según tu sistema

            if formato == 'video':
                yt_opts = {
                    "format": "bestvideo+bestaudio/best",
                    "outtmpl": outtmpl,
                    "noplaylist": True,
                    "ffmpeg_location": ffmpeg_path,
                }
            elif formato == 'audio':
                yt_opts = {
                    "format": "bestaudio/best",
                    "outtmpl": outtmpl,
                    "ffmpeg_location": ffmpeg_path,
                    "noplaylist": True,
                    "postprocessors": [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }],
                }
            else:
                return render(request, 'descargar.html', {
                    'error': 'Formato no soportado. Elige Audio o Video.'
                })

            # 📥 Descargar archivo
            with yt_dlp.YoutubeDL(yt_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                archivo_descargado = ydl.prepare_filename(info)

                if formato == 'audio':
                    archivo_descargado = os.path.splitext(archivo_descargado)[0] + '.mp3'
                else:
                    archivo_descargado = os.path.splitext(archivo_descargado)[0] + '.mp4'

            # 🪄 Nombre limpio y único
            nombre_limpio = limpiar_nombre(os.path.basename(archivo_descargado))
            nombre_unico = f"{uuid.uuid4().hex}_{nombre_limpio}"
            ruta_final = os.path.join(temp_dir, nombre_unico)

            os.rename(archivo_descargado, ruta_final)

            # 📤 Respuesta en streaming + cleanup automático
            response = StreamingHttpResponse(
                file_iterator(ruta_final, temp_dir),
                content_type="application/octet-stream"
            )
            response['Content-Disposition'] = f'attachment; filename="{nombre_limpio}"'
            return response

        return render(request, 'descargar.html')

    except Exception:
        error = traceback.format_exc()
        return render(request, 'descargar.html', {"error": f"Ocurrió un error:\n{error}"})
