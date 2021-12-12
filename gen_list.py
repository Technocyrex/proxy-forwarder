from server import PORT_NUM, AUTH_KEY
from http.client import HTTPSConnection

def get_ip():
    conn = HTTPSConnection("api.ipify.org")
    try:
        conn.request("GET", "/?format=text")
        resp = conn.getresponse()
        ip = resp.read().decode().strip()
        return ip
    finally:
        conn.close()

ip = get_ip()
with open("proxies.txt") as fp:
    proxy_count = len(fp.read().splitlines())

with open("new_proxies.txt", "w") as fp:
    fp.write("\n".join([
        f"{index}:{AUTH_KEY}@{ip}:{PORT_NUM}"
        for index in range(proxy_count)
    ]))