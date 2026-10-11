"""
Servidor web del bot.

Rutas:
  /webhook         → la que usa WhatsApp (Meta) para mandar y verificar mensajes
  /simulador       → un chat en el navegador para probar el bot sin WhatsApp
  /turnos?clave=…  → lista de próximos turnos para el dueño del negocio

Uso:  python app.py   (y abrí http://localhost:5000/simulador)
"""
import logging
import os
from datetime import datetime

from flask import Flask, abort, jsonify, render_template, request

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import config
import whatsapp
from bot import Bot, fecha_linda

app = Flask(__name__)
bot = Bot()
logging.basicConfig(level=logging.INFO)
CLAVE_ADMIN = os.getenv("CLAVE_ADMIN", "")


# ---------- WhatsApp ----------
@app.get("/webhook")
def verificar_webhook():
    """Meta llama acá una sola vez para comprobar que el webhook es nuestro."""
    if (request.args.get("hub.mode") == "subscribe"
            and whatsapp.VERIFY_TOKEN
            and request.args.get("hub.verify_token") == whatsapp.VERIFY_TOKEN):
        return request.args.get("hub.challenge", ""), 200
    abort(403)


@app.post("/webhook")
def recibir_mensaje():
    for telefono, texto in whatsapp.mensajes_entrantes(request.get_json(silent=True) or {}):
        app.logger.info("Mensaje de %s: %s", telefono, texto)
        if texto == "__no_texto__":
            respuestas = ["Por ahora solo entiendo mensajes de texto 🙂 Escribí *menu* para empezar."]
        else:
            respuestas = bot.responder(telefono, texto)
        for respuesta in respuestas:
            try:
                whatsapp.enviar_texto(telefono, respuesta)
            except Exception:
                app.logger.exception("No se pudo enviar el mensaje a %s", telefono)
    return "ok", 200  # siempre 200: si no, Meta reintenta el mismo mensaje


# ---------- Simulador ----------
@app.get("/simulador")
def simulador():
    return render_template("simulador.html", negocio=config.NEGOCIO)


@app.post("/simulador/mensaje")
def simulador_mensaje():
    datos = request.get_json(force=True)
    telefono = "sim-" + str(datos.get("telefono", "demo"))[:20]
    return jsonify(respuestas=bot.responder(telefono, datos.get("texto", "")))


# ---------- Vista del dueño ----------
@app.get("/turnos")
def ver_turnos():
    if not CLAVE_ADMIN or request.args.get("clave") != CLAVE_ADMIN:
        abort(403)
    ahora = datetime.now(config.ZONA_HORARIA)
    turnos = []
    for t in bot.agenda.proximos_turnos(ahora):
        inicio = datetime.fromisoformat(t["inicio"])
        turnos.append({**t, "dia": fecha_linda(inicio), "hora": f"{inicio:%H:%M}"})
    return render_template("turnos.html", negocio=config.NEGOCIO, turnos=turnos)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=False)
