import asyncio
import socket
import struct
from .stanag_server_protocol import StanagServerProtocol

async def createUDPServer(loop, message_callback, port_rx = 4586, port_tx = 4587, addr_rx = "224.10.10.10", addr_tx = "224.10.10.10"):
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', port_rx))
    group = socket.inet_aton(addr_rx)
    mreq = struct.pack('4sL', group, socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

    transport, protocol = await loop.create_datagram_endpoint(
        lambda: StanagServerProtocol(loop, message_callback, port_rx, addr_tx),
        sock=sock,
    )
    
    return (transport, protocol)