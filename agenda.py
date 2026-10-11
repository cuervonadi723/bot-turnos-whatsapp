"""
La agenda: guarda los turnos en SQLite y calcula qué horarios están libres.
No sabe nada de WhatsApp: solo de días, horas y turnos.
"""
import json
import sqlite3
from datetime import datetime, timedelta

import config


class Agenda:
    def __init__(self, ruta_db=None):
        self.db = sqlite3.connect(ruta_db or config.BASE_DE_DATOS, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS turnos (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                telefono  TEXT NOT NULL,
                nombre    TEXT NOT NULL,
                servicio  TEXT NOT NULL,
                inicio    TEXT NOT NULL,   -- fecha y hora en formato ISO
                fin       TEXT NOT NULL,
                estado    TEXT NOT NULL DEFAULT 'activo'  -- activo | cancelado
            );
            CREATE TABLE IF NOT EXISTS conversaciones (
                telefono  TEXT PRIMARY KEY,
                paso      TEXT NOT NULL,
                datos     TEXT NOT NULL DEFAULT '{}'
            );
        """)

    # ---------- Disponibilidad ----------
    def dias_con_atencion(self, ahora):
        """Los próximos días en que el negocio abre, empezando por hoy."""
        dias, fecha = [], ahora.date()
        while len(dias) < config.DIAS_A_MOSTRAR:
            if config.HORARIOS.get(fecha.weekday()):
                dias.append(fecha)
            fecha += timedelta(days=1)
        return dias

    def horarios_libres(self, fecha, minutos, ahora):
        """Horas de inicio en las que entra un servicio de `minutos` sin pisar otro turno."""
        horario = config.HORARIOS.get(fecha.weekday())
        if not horario:
            return []
        tz = config.ZONA_HORARIA
        abre = datetime.combine(fecha, datetime.strptime(horario[0], "%H:%M").time(), tz)
        cierra = datetime.combine(fecha, datetime.strptime(horario[1], "%H:%M").time(), tz)
        limite = ahora + timedelta(minutes=config.ANTICIPACION_MINUTOS)
        ocupados = self._turnos_del_dia(fecha)

        libres, inicio = [], abre
        while inicio + timedelta(minutes=minutos) <= cierra:
            fin = inicio + timedelta(minutes=minutos)
            choca = any(inicio < o_fin and fin > o_ini for o_ini, o_fin in ocupados)
            if inicio >= limite and not choca:
                libres.append(inicio)
            inicio += timedelta(minutes=config.INTERVALO_MINUTOS)
        return libres

    def _turnos_del_dia(self, fecha):
        filas = self.db.execute(
            "SELECT inicio, fin FROM turnos WHERE estado = 'activo' AND inicio LIKE ?",
            (fecha.isoformat() + "%",),
        ).fetchall()
        return [(datetime.fromisoformat(f["inicio"]), datetime.fromisoformat(f["fin"])) for f in filas]

    # ---------- Turnos ----------
    def reservar(self, telefono, nombre, servicio, inicio, ahora):
        """Guarda el turno si el horario sigue libre. Devuelve el id, o None si lo ganó otro."""
        fin = inicio + timedelta(minutes=servicio["minutos"])
        with self.db:  # transacción: la verificación y el guardado van juntos
            if inicio not in self.horarios_libres(inicio.date(), servicio["minutos"], ahora):
                return None
            cursor = self.db.execute(
                "INSERT INTO turnos (telefono, nombre, servicio, inicio, fin) VALUES (?, ?, ?, ?, ?)",
                (telefono, nombre, servicio["nombre"], inicio.isoformat(), fin.isoformat()),
            )
            return cursor.lastrowid

    def turnos_de(self, telefono, ahora):
        """Turnos activos y futuros de una persona."""
        filas = self.db.execute(
            "SELECT * FROM turnos WHERE telefono = ? AND estado = 'activo' ORDER BY inicio",
            (telefono,),
        ).fetchall()
        return [dict(f) for f in filas if datetime.fromisoformat(f["inicio"]) > ahora]

    def cancelar(self, turno_id, telefono):
        with self.db:
            cursor = self.db.execute(
                "UPDATE turnos SET estado = 'cancelado' WHERE id = ? AND telefono = ? AND estado = 'activo'",
                (turno_id, telefono),
            )
            return cursor.rowcount == 1

    def proximos_turnos(self, ahora):
        """Todos los turnos activos desde ahora (para la vista del dueño)."""
        filas = self.db.execute(
            "SELECT * FROM turnos WHERE estado = 'activo' AND inicio >= ? ORDER BY inicio",
            (ahora.isoformat(),),
        ).fetchall()
        return [dict(f) for f in filas]

    # ---------- Estado de cada conversación ----------
    def leer_conversacion(self, telefono):
        fila = self.db.execute(
            "SELECT paso, datos FROM conversaciones WHERE telefono = ?", (telefono,)
        ).fetchone()
        return (fila["paso"], json.loads(fila["datos"])) if fila else ("inicio", {})

    def guardar_conversacion(self, telefono, paso, datos):
        with self.db:
            self.db.execute(
                "INSERT INTO conversaciones (telefono, paso, datos) VALUES (?, ?, ?) "
                "ON CONFLICT(telefono) DO UPDATE SET paso = excluded.paso, datos = excluded.datos",
                (telefono, paso, json.dumps(datos)),
            )
