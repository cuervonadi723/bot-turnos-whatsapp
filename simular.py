"""
Probar el bot desde la consola, sin WhatsApp ni navegador.
Uso:  python simular.py      (escribí "salir" para terminar)
"""
from bot import Bot

bot = Bot()
print('Simulador del bot. Escribí "hola" para empezar y "salir" para terminar.\n')
while True:
    texto = input("Vos: ")
    if texto.strip().lower() == "salir":
        break
    for respuesta in bot.responder("consola", texto):
        print("\nBot:", respuesta.replace("*", ""), "\n")
