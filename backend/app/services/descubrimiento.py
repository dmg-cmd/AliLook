"""Servicio de descubrimiento automático en red local mediante UDP."""

import json
import os
import socket
import threading
from typing import Optional

PUERTO_DESCUBRIMIENTO = 8001
MENSAJE_PETICION = b"PROYECTO_ALI_DISCOVER"


def _obtener_ip_hacia_cliente(ip_cliente: str) -> str:
    """Determina la IP local de la interfaz que enruta hacia el cliente."""
    host_fijo = os.getenv("VTO_HOST_ANUNCIADO", "").strip()
    if host_fijo and host_fijo != "0.0.0.0":
        return host_fijo

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect((ip_cliente, 1))
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


class ServidorDescubrimientoUDP:
    """Responde a peticiones UDP broadcast de la app Android con la IP del servidor."""

    def __init__(self, puerto_http: int = 8000, puerto_udp: int = PUERTO_DESCUBRIMIENTO) -> None:
        self.puerto_http = puerto_http
        self.puerto_udp = puerto_udp
        self._activo = False
        self._hilo: Optional[threading.Thread] = None
        self._sock: Optional[socket.socket] = None

    def iniciar(self) -> None:
        if self._activo:
            return
        self._activo = True
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("0.0.0.0", self.puerto_udp))
        self._sock.settimeout(0.5)
        self._hilo = threading.Thread(target=self._bucle, daemon=True)
        self._hilo.start()

    def _bucle(self) -> None:
        assert self._sock is not None
        while self._activo:
            try:
                datos, addr = self._sock.recvfrom(1024)
            except socket.timeout:
                continue
            except OSError:
                break

            if datos.strip() == MENSAJE_PETICION:
                ip_servidor = _obtener_ip_hacia_cliente(addr[0])
                respuesta = json.dumps(
                    {
                        "servicio": "proyecto_ali",
                        "ip": ip_servidor,
                        "puerto": self.puerto_http,
                    }
                ).encode("utf-8")
                self._sock.sendto(respuesta, addr)

    def detener(self) -> None:
        self._activo = False
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
        if self._hilo is not None:
            self._hilo.join(timeout=1.5)
