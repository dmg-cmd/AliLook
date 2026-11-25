"""Pruebas unitarias para el descubrimiento automático UDP."""

import json
import socket
from app.services.descubrimiento import MENSAJE_PETICION, ServidorDescubrimientoUDP


def test_descubrimiento_udp_responde_ip_y_puerto():
    servidor = ServidorDescubrimientoUDP(puerto_http=8000, puerto_udp=18001)
    servidor.iniciar()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as cli:
            cli.settimeout(2.0)
            cli.sendto(MENSAJE_PETICION, ("127.0.0.1", 18001))
            datos, _ = cli.recvfrom(1024)
            payload = json.loads(datos.decode("utf-8"))
            assert payload["servicio"] == "proyecto_ali"
            assert payload["puerto"] == 8000
            assert isinstance(payload["ip"], str) and len(payload["ip"]) > 0
    finally:
        servidor.detener()
