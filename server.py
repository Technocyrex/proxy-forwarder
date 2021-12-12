from itertools import count
from base64 import b64decode
import multiprocessing
import threading
import socket

AUTH_KEY = "proxysecret123"
PORT_NUM = 5407
BLOCK_SIZE = 1024 ** 2
CLIENT_TIMEOUT = 60
PROXY_CONNECT_TIMEOUT = 5
PROXY_READ_TIMEOUT = 60
WORKER_COUNT = 64
THREAD_COUNT = 25

proxy_list = []
proxy_counter = count()

with open("proxies.txt", encoding="UTF-8", errors="ignore") as fp:
    for line in fp:
        addr, port = line.split(":", 1)
        proxy_list.append((addr.lower(), int(port)))
    proxy_list = list(set(proxy_list))

class Client:
    _sock: socket.socket
    _addr: tuple

    def __init__(self, sock, addr):
        self._sock = sock
        self._addr = addr
        self._proxy_sock = None
        self._alive = True
        self._threads = []

        self._sock.settimeout(CLIENT_TIMEOUT)

    def _add_thread(self, fn):
        thread = threading.Thread(
            target=self._server_chunk_forwarder
        )
        thread.start()
        self._threads.append(thread)

    def _server_chunk_forwarder(self):
        while self._alive:
            try:
                chunk = self._proxy_sock.recv(BLOCK_SIZE)
                if not chunk:
                    break
                self._sock.send(chunk)
            except:
                break
        self._alive = False

    def _setup_proxy(self, host_addr, proxy_addr):
        self._proxy_sock = socket.socket()
        self._proxy_sock.settimeout(PROXY_CONNECT_TIMEOUT)
        self._proxy_sock.connect(proxy_addr)
        self._proxy_sock.settimeout(PROXY_READ_TIMEOUT)
        self._proxy_sock.send((
            f"CONNECT {host_addr[0]}:{host_addr[1]} HTTP/1.1\r\n"
            f"\r\n"
        ).encode())
        response = self._proxy_sock.recv(4096)
        self._sock.sendall(response)

        if not (response.startswith(b"HTTP/1.1 200") or
                response.startswith(b"HTTP/1.0 200")):
            raise Exception(
                "Invalid CONNECT response from proxy server.")
            
    def process_connect_request(self):
        request = self._sock.recv(4096)

        if not request.startswith(b"CONNECT "):
            raise Exception("Invalid initial CONNECT request.")

        auth_info = None
        if b"uthorization: Basic " in request:
            auth_info = b64decode(request \
                .split(b"uthorization: Basic ", 1)[1] \
                .split(b"\n", 1)[0] \
                .strip()).decode().split(":", 1)
            auth_info[0] = (int(auth_info[0]) % len(proxy_list)) \
                           if auth_info[0].isdigit() else None
        
        if AUTH_KEY:
            if not auth_info:
                self.close(code=403, msg="Auth key is missing")
                return
            if auth_info[1] != AUTH_KEY:
                self.close(code=403, msg="Auth key is invalid")
                return

        host = request.split(b" ", 2)[1].decode()
        hostname, _, port = host.partition(":")
        port = int(port) if port else 80
        host_addr = (hostname, port)

        proxy_index = auth_info[0] \
                      if not auth_info or auth_info[0] is not None \
                      else next(proxy_counter)
        proxy_addr = proxy_list[proxy_index]

        self._setup_proxy(host_addr, proxy_addr)
        self._add_thread(self._server_chunk_forwarder)

    def forward_chunks(self):
        while self._alive:
            chunk = self._sock.recv(BLOCK_SIZE)
            if not chunk:
                self._alive = False
                break
            self._proxy_sock.send(chunk)

    def close(self, code=None, msg=None):
        if code and not self._proxy_sock:
            try:
                self._sock.send((
                    f"HTTP/1.1 {code} {msg or '-'}\r\n"
                    f"\r\n"
                ).encode())
            except:
                pass
        try: self._sock.shutdown(2)
        except OSError: pass
        self._sock.close()
        self._threads.clear()
        self._alive = False

def thread_func(server_sock: socket.socket):
    while True:
        client = Client(*server_sock.accept())
        try:
            client.process_connect_request()
            client.forward_chunks()
        except:
            pass
        finally:
            client.close()

def worker_func(server_sock: socket.socket):
    threads = [
        threading.Thread(
            target=thread_func,
            args=(server_sock,)
        )
        for _ in range(THREAD_COUNT)
    ]
    for t in threads: t.start()
    for t in threads: t.join()

if __name__ == "__main__":
    server_sock = socket.socket()
    server_sock.bind(("0.0.0.0", PORT_NUM))
    server_sock.listen()

    workers = [
        multiprocessing.Process(
            target=worker_func,
            args=(server_sock,)
        )
        for _ in range(WORKER_COUNT)
    ]
    for w in workers: w.start()
