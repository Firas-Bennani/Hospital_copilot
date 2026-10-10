"""
Lanceur de la plateforme : écoute en IPv4 **et** en IPv6.

    python serve.py [--port 8000] [--host 0.0.0.0]

Pourquoi : sous Windows, `localhost` est d'abord résolu en IPv6 (`::1`). Avec `uvicorn --host 0.0.0.0` (IPv4 seul),
chaque nouvelle connexion du navigateur à http://localhost:8000 attend ~3 s l'échec en IPv6 avant de retomber
sur 127.0.0.1 : l'interface semble figée par à-coups. n8n (Node) échouait pour la même raison.
`uvicorn server:app` reste utilisable tel quel (point d'entrée conservé).
"""

from __future__ import annotations

import argparse
import asyncio
import socket

import uvicorn


def listening_sockets(host: str, port: int) -> list[socket.socket]:
    socks: list[socket.socket] = []
    s4 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s4.bind((host, port))
    socks.append(s4)
    if host in ("0.0.0.0", "127.0.0.1"):
        try:
            s6 = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            s6.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
            s6.bind(("::" if host == "0.0.0.0" else "::1", port))
            socks.append(s6)
        except OSError:  # IPv6 désactivé sur la machine : IPv4 seul
            pass
    return socks


def main() -> None:
    ap = argparse.ArgumentParser(description="Hospital Copilot — serveur (IPv4 + IPv6)")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="0.0.0.0")
    args = ap.parse_args()
    socks = listening_sockets(args.host, args.port)
    server = uvicorn.Server(uvicorn.Config("server:app", log_level="info"))
    print(f"Hospital Copilot : http://localhost:{args.port}  ({' + '.join('IPv6' if s.family == socket.AF_INET6 else 'IPv4' for s in socks)})", flush=True)
    asyncio.run(server.serve(sockets=socks))


if __name__ == "__main__":
    main()
