# proxy-forwarder
 
A proxy server primarily meant for evading IP restrictions on a mass amount of proxies.

# Setup
1. Create a file named `proxies.txt` and fill it with your `HTTP` proxies.
2. Replace the `AUTH_KEY` constant in server.py with something secure.
3. Set your firewall to allow TCP port `5407`.
4. Run `server.py`.

# Usage
```python
import requests

#        proxy number       auth key
#                   v              v
proxy_url = "http://1:proxysecret123@127.0.0.1:5407"

resp = requests.get(
    url="https://api.ipify.org/?format=json",
    proxies={"https": proxy_url}
)
print(resp.json())
```