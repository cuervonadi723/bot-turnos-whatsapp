import os
from zoneinfo import ZoneInfo

NEGOCIO = "Barbería MILONADI"
DIRECCION = "Av. San Martín 1234, San Vicente, Santa Fe"
ZONA_HORARIA = ZoneInfo("America/Argentina/Buenos_Aires")

# Servicios: nombre, duración en minutos y precio en pesos
SERVICIOS = [
    {"nombre": "Corte de pelo", "minutos": 30, "precio": 8000},
    {"nombre": "Corte + barba", "minutos": 60, "precio": 11000},
    {"nombre": "Arreglo de barba", "minutos": 30, "precio": 5000},
    {"nombre": "Corte infantil", "minutos": 30, "precio": 6500},
    {"nombre": "Corte + lavado", "minutos": 45, "precio": 9500},
    {"nombre": "Tintura Mujer", "minutos": 150, "precio": 30000},
    {"nombre": "Tintura Hombre", "minutos": 90, "precio": 30000},
]

# Horario de atención por día de la semana (0 = lunes ... 6 = domingo).
# None = cerrado. Cada día: (hora de apertura, hora de cierre).
HORARIOS = {
    0: None,
    1: ("10:00", "20:00"),
    2: ("10:00", "20:00"),
    3: ("10:00", "20:00"),
    4: ("10:00", "20:00"),
    5: ("09:00", "14:00"),
    6: None,
}

INTERVALO_MINUTOS = 30     # cada cuánto empieza un turno posible
DIAS_A_MOSTRAR = 6         # cuántos días con atención se ofrecen para reservar
ANTICIPACION_MINUTOS = 60  # no se puede reservar con menos de esta anticipación
CANCELACION_MINUTOS = 120  # se puede cancelar hasta 2 horas antes

BASE_DE_DATOS = os.getenv("BASE_DE_DATOS", "turnos.db")
