"""
Pruebas automáticas del bot. Simulan conversaciones completas con una fecha fija.
Uso:  python -m unittest discover tests
"""
import os
import sys
import tempfile
import unittest
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
from agenda import Agenda  # noqa: E402
from bot import MENU, Bot  # noqa: E402

TZ = config.ZONA_HORARIA


class RelojFalso:
    def __init__(self, momento):
        self.momento = momento

    def __call__(self):
        return self.momento


class PruebasBot(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        # Domingo 11/10/2026 a las 20:00: la barbería está cerrada domingo y lunes
        self.reloj = RelojFalso(datetime(2026, 10, 11, 20, 0, tzinfo=TZ))
        self.bot = Bot(Agenda(self.tmp.name), self.reloj)

    def tearDown(self):
        self.bot.agenda.db.close()
        os.unlink(self.tmp.name)

    def charlar(self, telefono, *mensajes):
        respuestas = []
        for m in mensajes:
            respuestas = self.bot.responder(telefono, m)
        return "\n".join(respuestas)

    def test_saludo_muestra_menu(self):
        r = self.charlar("111", "hola")
        self.assertIn(config.NEGOCIO, r)
        self.assertIn("1. Sacar un turno", r)

    def test_reserva_completa(self):
        r = self.charlar("111", "hola", "1", "1")
        self.assertIn("1. Martes 13 oct", r)          # lunes cerrado: el primer día es martes
        self.assertNotIn("Lunes", r)
        r = self.charlar("111", "1")
        self.assertIn("1. 10:00", r)
        r = self.charlar("111", "1", "juan perez")
        self.assertIn("Juan Perez", r)
        r = self.charlar("111", "1")
        self.assertIn("✅", r)
        self.assertIn("Martes 13 oct a las 10:00", r)
        self.assertEqual(len(self.bot.agenda.turnos_de("111", self.reloj())), 1)

    def test_horario_ocupado_no_se_ofrece(self):
        self.charlar("111", "hola", "1", "1", "1", "1", "Ana", "1")   # Ana: martes 10:00
        r = self.charlar("222", "hola", "1", "1", "1")
        self.assertNotIn("10:00", r)
        self.assertIn("1. 10:30", r)

    def test_servicio_largo_no_pisa_otro_turno(self):
        # Turno de 30 min a las 10:30; un servicio de 60 min no puede empezar a las 10:00
        self.charlar("111", "hola", "1", "1", "1", "2", "Ana", "1")    # martes 10:30
        r = self.charlar("222", "hola", "1", "2", "1")                 # Corte + barba, martes
        self.assertNotIn("1. 10:00", r)
        self.assertIn("1. 11:00", r)

    def test_dos_personas_eligen_el_mismo_horario(self):
        self.charlar("111", "hola", "1", "1", "1", "1", "Ana")
        self.charlar("222", "hola", "1", "1", "1", "1", "Beto")
        self.assertIn("✅", self.charlar("111", "1"))
        r = self.charlar("222", "1")                                  # llegó tarde
        self.assertNotIn("✅", r)
        self.assertIn("Horarios libres", r)
        self.assertEqual(len(self.bot.agenda.proximos_turnos(self.reloj())), 1)

    def test_cancelar_turno(self):
        self.charlar("111", "hola", "1", "1", "1", "1", "Ana", "1")
        r = self.charlar("111", "2")
        self.assertIn("Tus turnos", r)
        r = self.charlar("111", "1")
        self.assertIn("cancelé", r)
        self.assertEqual(self.bot.agenda.turnos_de("111", self.reloj()), [])

    def test_no_se_cancela_a_ultimo_momento(self):
        self.charlar("111", "hola", "1", "1", "1", "1", "Ana", "1")
        self.reloj.momento = datetime(2026, 10, 13, 9, 0, tzinfo=TZ)  # falta 1 hora
        r = self.charlar("111", "2", "1")
        self.assertIn("ya no se puede cancelar", r)
        self.assertEqual(len(self.bot.agenda.turnos_de("111", self.reloj())), 1)

    def test_respuesta_invalida(self):
        r = self.charlar("111", "hola", "9")
        self.assertIn("No entendí", r)
        r = self.charlar("111", "1", "abc")
        self.assertIn("Elegí un número", r)

    def test_cero_vuelve_al_menu(self):
        r = self.charlar("111", "hola", "1", "1", "0")
        self.assertEqual(r, MENU)

    def test_hablar_con_persona_silencia_el_bot(self):
        self.charlar("111", "hola", "5")
        self.assertEqual(self.bot.responder("111", "necesito ayuda"), [])
        self.assertIn("1. Sacar un turno", self.charlar("111", "menu"))

    def test_sabado_cierra_temprano(self):
        r = self.charlar("111", "hola", "1", "1", "5")                 # 5 = sábado 17
        self.assertIn("Sábado 17 oct", r)
        self.assertIn("09:00", r)
        self.assertNotIn("14:00", r)                                  # cierra a las 14


if __name__ == "__main__":
    unittest.main()
