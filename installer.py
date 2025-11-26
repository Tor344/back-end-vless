import subprocess
import os
import json
import re
from pathlib import Path

CONFIG_PATH = "/usr/local/etc/xray/config.json"
KEYS_PATH = "/usr/local/etc/xray/.keys"
HELP_PATH = str(Path.home() / "help")

def run(cmd, capture_output=True, shell=True):
    """Run system command and return output"""
    result = subprocess.run(cmd, shell=shell, capture_output=capture_output, text=True)
    return result.stdout.strip()

def install_packages():
    run("apt update")
    run("apt install qrencode curl jq -y")

def enable_bbr():
    bbr_current = run("sysctl -a | grep net.ipv4.tcp_congestion_control")
    if "bbr" in bbr_current:
        print("bbr уже включен")
    else:
        with open("/etc/sysctl.conf", "a") as f:
            f.write("net.core.default_qdisc=fq\n")
            f.write("net.ipv4.tcp_congestion_control=bbr\n")
        run("sysctl -p")
        print("bbr включен")

def install_xray():
    run('bash -c "$(curl -4 -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install')
    if Path(KEYS_PATH).exists():
        os.remove(KEYS_PATH)
    # Генерируем .keys файл
    with open(KEYS_PATH, "w") as f:
        sid = run("openssl rand -hex 8")
        f.write(f"shortsid: {sid}\n")
        uuid = run("xray uuid")
        f.write(f"uuid: {uuid}\n")
        # xray x25519 выводит PrivateKey и PublicKey
        x25519_out = run("xray x25519")
        for line in x25519_out.splitlines():
            f.write(line.strip()+"\n")
    return

def extract_keys():
    keys = {}
    with open(KEYS_PATH) as f:
        for line in f:
            if ': ' in line:
                k, v = line.strip().split(': ', 1)
                keys[k.strip()] = v.strip()
            elif re.match(r'(PrivateKey|PublicKey):', line):
                k, v = line.strip().split(':', 1)
                keys[k.strip()] = v.strip()
    return keys

def create_config(keys):
    config = {
        "log": {"loglevel": "warning"},
        "routing": {
            "domainStrategy": "IPIfNonMatch",
            "rules": [{
                "type": "field",
                "domain": ["geosite:category-ads-all"],
                "outboundTag": "block"
            }]
        },
        "inbounds": [{
            "listen": "0.0.0.0",
            "port": 443,
            "protocol": "vless",
            "settings": {
                "clients": [{
                    "email": "main",
                    "id": keys["uuid"],
                    "flow": "xtls-rprx-vision"
                }],
                "decryption": "none"
            },
            "streamSettings": {
                "network": "tcp",
                "security": "reality",
                "realitySettings": {
                    "show": False,
                    "dest": "github.com:443",
                    "xver": 0,
                    "serverNames": ["github.com", "www.github.com"],
                    "privateKey": keys["PrivateKey"],
                    "minClientVer": "",
                    "maxClientVer": "",
                    "maxTimeDiff": 0,
                    "shortIds": [keys["shortsid"]]
                }
            },
            "sniffing": {
                "enabled": True,
                "destOverride": ["http", "tls"]
            }
        }],
        "outbounds": [
            {"protocol": "freedom", "tag": "direct"},
            {"protocol": "blackhole", "tag": "block"}
        ],
        "policy": {
            "levels": {
                "0": {"handshake": 3, "connIdle": 180}
            }
        }
    }
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=4)

def restart_xray():
    run("systemctl restart xray")

def create_help():
    helptext = """
Команды для управления пользователями Xray:

    mainuser - выводит ссылку для подключения основного пользователя
    newuser - создает нового пользователя
    rmuser - удаление пользователей
    sharelink - выводит список пользователей и позволяет создать для них ссылки для подключения
    userlist - выводит список клиентов

Файл конфигурации находится по адресу:

    /usr/local/etc/xray/config.json

Команда для перезагрузки ядра Xray:

    systemctl restart xray
"""
    with open(HELP_PATH, "w") as f:
        f.write(helptext)

def main():
    install_packages()
    enable_bbr()
    install_xray()
    keys = extract_keys()
    create_config(keys)
    restart_xray()
    create_help()
    print("Xray-core успешно установлен")

    # mainuser функция - вывод ссылки и QR-кода
    config = json.load(open(CONFIG_PATH))
    protocol = config["inbounds"][0]["protocol"]
    port = config["inbounds"][0]["port"]
    uuid = keys["uuid"]
    pbk = keys.get("Password", "")
    sid = keys["shortsid"]
    sni = config["inbounds"][0]["streamSettings"]["realitySettings"]["serverNames"][0]
    ip = run("curl -4 -s icanhazip.com")
    link = f"{protocol}://{uuid}@{ip}:{port}?security=reality&sni={sni}&fp=firefox&pbk={pbk}&sid={sid}&spx=/&type=tcp&flow=xtls-rprx-vision&encryption=none#vless-{ip}"
    print("Ссылка для подключения:\n", link)
    print("QR-код:")
    subprocess.run(f'echo {link} | qrencode -t ansiutf8', shell=True)

if __name__ == "__main__":
    main()
