"""
El cerebro del bot: recibe un mensaje y devuelve las respuestas.
Funciona igual para WhatsApp, el simulador web o la consola.

Cada conversación tiene un "paso" (en qué parte del diálogo está) y "datos"
(lo que la persona ya eligió). Eso se guarda en la base para no perderlo.
"""
from datetime import datetime

import config
from agenda import Agenda

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
SALUDOS = {"hola", "buenas", "buen dia", "buen día", "buenos dias", "buenos días",
           "buenas tardes", "buenas noches", "menu", "menú", "inicio", "0"}

MENU = (
    "¿En qué te puedo ayudar? Respondé con el número:\n\n"
    "1. Sacar un turno\n"
    "2. Ver o cancelar mi turno\n"
    "3. Servicios y precios\n"
    "4. Horarios y dirección\n"
    "5. Hablar con una persona"
)


def pesos(valor):
    return "$" + f"{valor:,}".replace(",", ".")


def fecha_linda(dt):
    return f"{DIAS[dt.weekday()]} {dt.day} {MESES[dt.month - 1]}"


class Bot:
    def __init__(self, agenda=None, reloj=None):
        self.agenda = agenda or Agenda()
        # El reloj se puede reemplazar en las pruebas para simular cualquier fecha
        self.reloj = reloj or (lambda: datetime.now(config.ZONA_HORARIA))

    def responder(self, telefono, texto):
        texto = (texto or "").strip()
        paso, datos = self.agenda.leer_conversacion(telefono)

        if texto == "0":  # "0" siempre vuelve al menú, sin volver a saludar
            self.agenda.guardar_conversacion(telefono, "menu", {})
            return [MENU]
        if texto.lower() in SALUDOS:
            paso, datos = "inicio", {}

        manejador = getattr(self, f"_paso_{paso}", self._paso_inicio)
        respuestas, paso_nuevo, datos = manejador(telefono, texto, datos)
        self.agenda.guardar_conversacion(telefono, paso_nuevo, datos)
        return respuestas

    # ---------- Menú principal ----------
    def _paso_inicio(self, telefono, texto, datos):
        return [f"¡Hola! Soy el asistente de {config.NEGOCIO} ", MENU], "menu", {}

    def _paso_menu(self, telefono, texto, datos):
        if texto == "1":
            return self._mostrar_servicios_para_elegir()
        if texto == "2":
            return self._mostrar_mis_turnos(telefono)
        if texto == "3":
            lineas = [f"• {s['nombre']} ({s['minutos']} min): {pesos(s['precio'])}" for s in config.SERVICIOS]
            return ["Servicios y precios:\n\n" + "\n".join(lineas), MENU], "menu", {}
        if texto == "4":
            return [self._texto_horarios(), MENU], "menu", {}
        if texto == "5":
            return ["Listo, le aviso a alguien del equipo y te responde por acá en cuanto pueda. 🙌\n"
                    "Si querés volver al menú, escribí *menu*."], "humano", {}
        return ["No entendí tu respuesta. " + MENU], "menu", {}

    def _paso_humano(self, telefono, texto, datos):
        # Mientras espera a una persona, el bot no responde (salvo que escriba "menu")
        return [], "humano", datos

    def _texto_horarios(self):
        lineas = []
        for i, nombre in enumerate(DIAS):
            h = config.HORARIOS.get(i)
            lineas.append(f"• {nombre}: {h[0]} a {h[1]}" if h else f"• {nombre}: cerrado")
        return f"📍 {config.DIRECCION}\n\nHorarios:\n" + "\n".join(lineas)

    # ---------- Sacar un turno ----------
    def _mostrar_servicios_para_elegir(self):
        lineas = [f"{i}. {s['nombre']} – {pesos(s['precio'])}" for i, s in enumerate(config.SERVICIOS, 1)]
        return ["¿Qué servicio querés?\n\n" + "\n".join(lineas) + "\n\n0. Volver al menú"], "servicio", {}

    def _paso_servicio(self, telefono, texto, datos):
        indice = self._numero(texto, len(config.SERVICIOS))
        if indice is None:
            return ["Elegí un número de la lista, o 0 para volver."], "servicio", datos
        datos = {"servicio": indice}
        return self._mostrar_dias(datos)

    def _mostrar_dias(self, datos, aviso=None):
        ahora = self.reloj()
        servicio = config.SERVICIOS[datos["servicio"]]
        dias = [d for d in self.agenda.dias_con_atencion(ahora)
                if self.agenda.horarios_libres(d, servicio["minutos"], ahora)]
        if not dias:
            return ["Uh, no quedan turnos libres en los próximos días. Escribinos más adelante o elegí 5 en el menú.",
                    MENU], "menu", {}
        datos["dias"] = [d.isoformat() for d in dias]
        lineas = [f"{i}. {fecha_linda(d)}" for i, d in enumerate(dias, 1)]
        texto = f"{servicio['nombre']}. ¿Qué día te queda bien?\n\n" + "\n".join(lineas) + "\n\n0. Volver al menú"
        return ([aviso] if aviso else []) + [texto], "dia", datos

    def _paso_dia(self, telefono, texto, datos):
        indice = self._numero(texto, len(datos["dias"]))
        if indice is None:
            return ["Elegí un número de la lista, o 0 para volver."], "dia", datos
        datos["dia"] = datos["dias"][indice]
        return self._mostrar_horas(datos)

    def _mostrar_horas(self, datos):
        ahora = self.reloj()
        servicio = config.SERVICIOS[datos["servicio"]]
        dia = datetime.fromisoformat(datos["dia"]).date()
        horas = self.agenda.horarios_libres(dia, servicio["minutos"], ahora)
        if not horas:
            return self._mostrar_dias(datos, aviso="Ese día se llenó recién. Elegí otro:")
        datos["horas"] = [h.isoformat() for h in horas]
        opciones = [f"{i}. {h:%H:%M}" for i, h in enumerate(horas, 1)]
        # Tres horarios por línea, para que la lista no sea eterna en el celular
        lineas = ["    ".join(opciones[i:i + 3]) for i in range(0, len(opciones), 3)]
        return [f"Horarios libres el {fecha_linda(dia)}:\n\n" + "\n".join(lineas) + "\n\n0. Volver al menú"], "hora", datos

    def _paso_hora(self, telefono, texto, datos):
        indice = self._numero(texto, len(datos["horas"]))
        if indice is None:
            return ["Elegí un número de la lista, o 0 para volver."], "hora", datos
        datos["hora"] = datos["horas"][indice]
        return ["¿A nombre de quién reservo el turno?"], "nombre", datos

    def _paso_nombre(self, telefono, texto, datos):
        if len(texto) < 2 or texto.isdigit():
            return ["Escribime tu nombre, por favor."], "nombre", datos
        datos["nombre"] = texto[:40].title()
        servicio = config.SERVICIOS[datos["servicio"]]
        inicio = datetime.fromisoformat(datos["hora"])
        resumen = (f"Revisá los datos:\n\n"
                   f"👤 {datos['nombre']}\n✂️ {servicio['nombre']} ({pesos(servicio['precio'])})\n"
                   f"📅 {fecha_linda(inicio)} a las {inicio:%H:%M}\n\n"
                   f"1. Confirmar\n2. Cambiar el horario\n0. Cancelar y volver al menú")
        return [resumen], "confirmar", datos

    def _paso_confirmar(self, telefono, texto, datos):
        if texto == "2":
            return self._mostrar_dias(datos)
        if texto != "1":
            return ["Respondé 1 para confirmar, 2 para cambiar el horario o 0 para volver."], "confirmar", datos
        servicio = config.SERVICIOS[datos["servicio"]]
        inicio = datetime.fromisoformat(datos["hora"])
        turno_id = self.agenda.reservar(telefono, datos["nombre"], servicio, inicio, self.reloj())
        if turno_id is None:
            return self._mostrar_horas(datos) if self._hay_horas(datos) else self._mostrar_dias(datos)
        return [f"✅ ¡Listo, {datos['nombre']}! Te esperamos el {fecha_linda(inicio)} a las {inicio:%H:%M}.\n"
                f"📍 {config.DIRECCION}\n\n"
                "Si no podés venir, cancelalo desde el menú (opción 2). Escribí *menu* cuando quieras."], "menu", {}

    def _hay_horas(self, datos):
        servicio = config.SERVICIOS[datos["servicio"]]
        dia = datetime.fromisoformat(datos["dia"]).date()
        return bool(self.agenda.horarios_libres(dia, servicio["minutos"], self.reloj()))

    # ---------- Ver o cancelar ----------
    def _mostrar_mis_turnos(self, telefono):
        turnos = self.agenda.turnos_de(telefono, self.reloj())
        if not turnos:
            return ["No tenés turnos reservados.", MENU], "menu", {}
        lineas = []
        for i, t in enumerate(turnos, 1):
            inicio = datetime.fromisoformat(t["inicio"])
            lineas.append(f"{i}. {t['servicio']} – {fecha_linda(inicio)} {inicio:%H:%M}")
        texto = ("Tus turnos:\n\n" + "\n".join(lineas) +
                 "\n\nSi querés cancelar uno, respondé con su número. 0 para volver al menú.")
        return [texto], "cancelar", {"turnos": [t["id"] for t in turnos]}

    def _paso_cancelar(self, telefono, texto, datos):
        indice = self._numero(texto, len(datos["turnos"]))
        if indice is None:
            return ["Elegí un número de la lista, o 0 para volver."], "cancelar", datos
        turno_id = datos["turnos"][indice]
        turno = next((t for t in self.agenda.turnos_de(telefono, self.reloj()) if t["id"] == turno_id), None)
        if turno is None:
            return ["Ese turno ya no está activo.", MENU], "menu", {}
        inicio = datetime.fromisoformat(turno["inicio"])
        minutos_faltan = (inicio - self.reloj()).total_seconds() / 60
        if minutos_faltan < config.CANCELACION_MINUTOS:
            horas = config.CANCELACION_MINUTOS // 60
            return [f"Ese turno es en menos de {horas} horas y ya no se puede cancelar por acá. "
                    "Elegí 5 en el menú para hablar con alguien.", MENU], "menu", {}
        self.agenda.cancelar(turno_id, telefono)
        return [f"Listo, cancelé tu turno del {fecha_linda(inicio)} a las {inicio:%H:%M}.", MENU], "menu", {}

    # ---------- Utilidades ----------
    @staticmethod
    def _numero(texto, maximo):
        """Convierte '2' en el índice 1. Devuelve None si no es un número válido de la lista."""
        if texto.isdigit() and 1 <= int(texto) <= maximo:
            return int(texto) - 1
        return None
