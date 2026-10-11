"""
Conexión con la API de WhatsApp Cloud (Meta).
Solo hace dos cosas: leer los mensajes que llegan y enviar respuestas de texto.
"""
import os

import requests

TOKEN = os.getenv("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
# Meta publica versiones nuevas de la API seguido: revisá cuál es la actual en su documentación
API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v21.0")


def mensajes_entrantes(cuerpo):
    """Extrae (teléfono, texto) de lo que manda Meta al webhook. Ignora estados de entrega, fotos, etc."""
    for entrada in cuerpo.get("entry", []):
        for cambio in entrada.get("changes", []):
            for mensaje in cambio.get("value", {}).get("messages", []):
                if mensaje.get("type") == "text":
                    yield mensaje["from"], mensaje["text"]["body"]
                elif mensaje.get("type") == "interactive":
                    respuesta = mensaje["interactive"].get("button_reply") or mensaje["interactive"].get("list_reply")
                    if respuesta:
                        yield mensaje["from"], respuesta["id"]
                else:
                    # Audio, foto, sticker, etc.: le pedimos que escriba
                    yield mensaje["from"], "__no_texto__"


def enviar_texto(telefono, texto):
    if not TOKEN or not PHONE_NUMBER_ID:
        raise RuntimeError("Faltan WHATSAPP_TOKEN o WHATSAPP_PHONE_NUMBER_ID en el archivo .env")
    url = f"https://graph.facebook.com/{API_VERSION}/{PHONE_NUMBER_ID}/messages"
    respuesta = requests.post(
        url,
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={
            "messaging_product": "whatsapp",
            "to": telefono,
            "type": "text",
            "text": {"body": texto},
        },
        timeout=15,
    )
    respuesta.raise_for_status()
    return respuesta.json()
