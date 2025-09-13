from django.http import StreamingHttpResponse
from django.shortcuts import render
import os
import yt_dlp
import traceback
import re
import tempfile
import shutil
import uuid
import requests


# ----------------------------
# Funciones auxiliares
# ----------------------------

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
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception as e:
            print(f"[WARN] No se pudo limpiar: {e}")


def verificar_captcha(token):
    """Verifica el reCAPTCHA v3 con Google"""
    secret_key = "6Ld6dcErAAAAACjVfQKQ3bxFtnsOkan_0NQ5rnqm"  # <-- tu clave secreta v3
    url = "https://www.google.com/recaptcha/api/siteverify"
    data = {"secret": secret_key, "response": token}
    try:
        resp = requests.post(url, data=data, timeout=5)
        result = resp.json()
        print(f"[DEBUG CAPTCHA] Respuesta de Google: {result}")
        # Verifica éxito y score
        return result.get("success", False) and result.get("score", 0) >= 0.5
    except Exception as e:
        print(f"[ERROR CAPTCHA] {e}")
        return False


# ----------------------------
# Vista principal
# ----------------------------

def descargar(request):
    try:
        if request.method == 'POST':
            url = request.POST.get('url')
            formato = request.POST.get('formato')
            captcha_token = request.POST.get("g-recaptcha-response")
            print(f"[INFO] Formato solicitado: {formato}")
            print(f"[INFO] Token CAPTCHA recibido: {captcha_token}")

            # Verificación CAPTCHA
            if not captcha_token or not verificar_captcha(captcha_token):
                return render(request, "descargar.html", {
                    "error": "Debes completar el CAPTCHA correctamente antes de descargar."
                })

            if not url:
                return render(request, 'descargar.html', {
                    'error': 'Por favor, ingresa una URL válida.'
                })

            print(f"[INFO] Descargando: {url} en formato {formato}")

            # Carpeta temporal
            temp_dir = tempfile.mkdtemp()
            outtmpl = os.path.join(temp_dir, "%(title)s.%(ext)s")
            ffmpeg_path = "/usr/bin/ffmpeg"
            cookies_path = '/run/secrets/cookies.txt'  # Render lo monta aquí

            if not os.path.exists(ffmpeg_path):
                print(f"[WARN] ffmpeg no encontrado en {ffmpeg_path}")
            if not os.path.exists(cookies_path):
                print(f"[WARN] Cookies no encontradas en {cookies_path}")

            # Opciones de yt-dlp
            if formato == 'video':
                yt_opts = {
                    "format": "bestvideo+bestaudio/best",
                    "outtmpl": outtmpl,
                    "noplaylist": True,
                    "ffmpeg_location": ffmpeg_path,
                    "cookiefile": cookies_path if os.path.exists(cookies_path) else None,
                }
            elif formato == 'audio':
                yt_opts = {
                    "format": "bestaudio/best",
                    "outtmpl": outtmpl,
                    "noplaylist": True,
                    "ffmpeg_location": ffmpeg_path,
                    "cookiefile": cookies_path if os.path.exists(cookies_path) else None,
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

            # Descargar con yt-dlp
            try:
                with yt_dlp.YoutubeDL(yt_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    archivo_descargado = ydl.prepare_filename(info)
            except Exception as e:
                print(f"[ERROR YT-DLP] {traceback.format_exc()}")
                return render(request, 'descargar.html', {
                    "error": f"No se pudo descargar el contenido. Error: {e}"
                })

            # Ajustar extensión final
            if formato == 'audio':
                archivo_descargado = os.path.splitext(archivo_descargado)[0] + '.mp3'
            else:
                archivo_descargado = os.path.splitext(archivo_descargado)[0] + '.mp4'

            # Nombre limpio y único
            nombre_limpio = limpiar_nombre(os.path.basename(archivo_descargado))
            nombre_unico = f"{uuid.uuid4().hex}_{nombre_limpio}"
            ruta_final = os.path.join(temp_dir, nombre_unico)

            try:
                os.rename(archivo_descargado, ruta_final)
            except Exception as e:
                print(f"[WARN] No se pudo renombrar: {e}, usando archivo original")
                ruta_final = archivo_descargado

            # StreamingHttpResponse para descarga
            response = StreamingHttpResponse(
                file_iterator(ruta_final, temp_dir),
                content_type="application/octet-stream"
            )
            response['Content-Disposition'] = f'attachment; filename=\"{nombre_limpio}\"'
            print(f"[INFO] Archivo listo para descarga: {nombre_limpio}")
            return response

        # GET: renderizar formulario
        return render(request, 'descargar.html')

    except Exception:
        error = traceback.format_exc()
        print(f"[ERROR GENERAL] {error}")
        return render(request, 'descargar.html', {"error": f"Ocurrió un error:\n{error}"})
