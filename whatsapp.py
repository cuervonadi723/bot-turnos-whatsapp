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
# (v25.0 vence en julio de 2028)
API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v25.0")
NO_ESTA_EN_LISTA = 131030  # error de Meta: el número no está en la lista de destinatarios de prueba


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


_formato_que_anda = {}  # recuerda qué formato aceptó Meta para cada número


def _variantes_argentina(telefono):
    """
    WhatsApp manda los números de Argentina como 549 + área + número. Con el número de
    prueba de Meta, la lista de destinatarios a veces los guarda en otro formato:
    sin el 9, o con el 15 entre el área y el número. Probamos esas variantes.
    Solo se usan si Meta responde "no está en la lista", que pasa únicamente en modo prueba.
    """
    if not (telefono.startswith("549") and len(telefono) == 13):
        return []
    resto = telefono[3:]  # área + número: 10 dígitos
    variantes = ["54" + resto]
    for largo_area in (2, 3, 4):  # Buenos Aires = 11, Rosario = 341, San Vicente = 3492, etc.
        variantes.append("54" + resto[:largo_area] + "15" + resto[largo_area:])
    return variantes


def _codigo_error(respuesta):
    try:
        return respuesta.json().get("error", {}).get("code")
    except ValueError:
        return None


def _post(telefono, texto):
    url = f"https://graph.facebook.com/{API_VERSION}/{PHONE_NUMBER_ID}/messages"
    return requests.post(
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


def enviar_texto(telefono, texto):
    if not TOKEN or not PHONE_NUMBER_ID:
        raise RuntimeError("Faltan WHATSAPP_TOKEN o WHATSAPP_PHONE_NUMBER_ID en el archivo .env")
    destino = _formato_que_anda.get(telefono, telefono)
    respuesta = _post(destino, texto)
    if not respuesta.ok and _codigo_error(respuesta) == NO_ESTA_EN_LISTA:
        for alternativo in _variantes_argentina(telefono):
            if alternativo == destino:
                continue
            respuesta = _post(alternativo, texto)
            if respuesta.ok:
                _formato_que_anda[telefono] = alternativo
                break
            if _codigo_error(respuesta) != NO_ESTA_EN_LISTA:
                break
    if not respuesta.ok:
        # Mostramos el detalle que da Meta: ayuda mucho a entender qué falló
        raise RuntimeError(f"WhatsApp respondió {respuesta.status_code}: {respuesta.text}")
    return respuesta.json()
