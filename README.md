# Bot de turnos por WhatsApp

Bot para que los clientes de un negocio saquen, consulten y cancelen turnos por WhatsApp, sin intervención humana. El ejemplo está armado para una barbería, pero se adapta a cualquier negocio con turnos (peluquería, podología, consultorio, taller) cambiando un solo archivo.

## Qué hace

- Menú con opciones numeradas: sacar turno, ver o cancelar, servicios y precios, horarios y dirección, hablar con una persona.
- Muestra solo días y horarios **realmente libres**, según la duración de cada servicio (un servicio de 60 minutos no pisa un turno de las 10:30).
- No ofrece turnos con menos de 1 hora de anticipación y no deja cancelar a menos de 2 horas.
- Si dos personas eligen el mismo horario al mismo tiempo, solo una lo consigue y a la otra le ofrece los horarios que quedan.
- Opción "Hablar con una persona": el bot se calla hasta que el cliente escribe *menu*.
- Página para el dueño con la lista de próximos turnos.
- Simulador web con aspecto de WhatsApp para probarlo sin conectar nada.

## Estructura

| Archivo | Qué tiene |
| --- | --- |
| `config.py` | Datos del negocio: nombre, servicios, precios, horarios. Para otro cliente, se cambia esto. |
| `agenda.py` | La agenda: guarda turnos en SQLite y calcula horarios libres. |
| `bot.py` | El diálogo: qué responder en cada paso de la conversación. |
| `whatsapp.py` | Conexión con la API de WhatsApp Cloud de Meta. |
| `app.py` | Servidor web: webhook de WhatsApp, simulador y lista de turnos. |
| `simular.py` | Probar el bot desde la consola. |
| `tests/` | 11 pruebas automáticas de conversaciones completas. |

## Probarlo en tu computadora

Necesitás Python 3.10 o más nuevo.

```bash
pip install -r requirements.txt
python simular.py                 # en la consola
python app.py                     # o en el navegador: http://localhost:5000/simulador
python -m unittest discover tests # correr las pruebas
```

## Conectarlo a WhatsApp (número de prueba gratis)

Meta cambia sus pantallas seguido; si algo no coincide, buscá el paso equivalente en la [documentación de WhatsApp Cloud API](https://developers.facebook.com/docs/whatsapp/cloud-api/get-started).

1. Entrá a [developers.facebook.com](https://developers.facebook.com), creá una cuenta de desarrollador y una app de tipo **Business**.
2. Agregale el producto **WhatsApp**. Meta te da un **número de prueba** gratis.
3. En **Configuración de la API**, agregá tu propio número de celular como destinatario de prueba.
4. Copiá el **token de acceso temporal** y el **Phone number ID** al archivo `.env` (usá `.env.example` como modelo). El token temporal dura 24 horas; para algo permanente hay que crear un usuario del sistema.
5. El webhook necesita una dirección pública con HTTPS. Para probar desde tu computadora podés usar un túnel (por ejemplo ngrok o Cloudflare Tunnel) apuntando al puerto 5000. Para dejarlo funcionando siempre, se sube a un hosting (Render, Railway, un VPS).
6. En **Configuración > Webhook**, poné la dirección pública terminada en `/webhook` y el mismo `WHATSAPP_VERIFY_TOKEN` del `.env`. Suscribite al campo **messages**.
7. Mandale "hola" al número de prueba desde tu celular.

## Para un cliente real

- Un número de WhatsApp Business propio y la verificación del negocio en Meta.
- Hosting que esté encendido las 24 horas.
- Revisar los costos de conversaciones de Meta según el país.
- Opcional: conectar la agenda con Google Calendar, recordatorios automáticos el día anterior, botones en lugar de números.
