from server import PORT_NUM, AUTH_KEY
import requests

ip = requests.get("https://api.ipify.org?format=json").json()["ip"]

with open("proxies.txt") as fp:
    proxy_count = len(fp.read().splitlines())

with open("new_proxies.txt", "w") as fp:
    fp.write("\n".join([
        f"{index}:{AUTH_KEY}@{ip}:{PORT_NUM}"
        for index in range(proxy_count)
    ]))