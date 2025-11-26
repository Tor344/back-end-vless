"""
Менеджер пользователей Xray (VLESS + REALITY).

Зависимости из стандартной библиотеки:
    - json
    - os
    - subprocess
    - sys

Внешние бинарники (должны быть установлены в системе):
    - xray
    - qrencode
    - curl
"""

import json
import os
import subprocess
import sys

CONFIG_PATH = "/usr/local/etc/xray/config.json"
KEYS_PATH = "/usr/local/etc/xray/.keys"


def run(cmd: str) -> str:
    """Запуск shell-команды и возврат stdout."""
    result = subprocess.run(
        cmd,
        shell=True,
        check=False,
        capture_output=True,
        text=True
    )
    return result.stdout.strip()


def load_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        print(f"Файл конфигурации не найден: {CONFIG_PATH}")
        sys.exit(1)
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def save_config(cfg: dict) -> None:
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=4)


def load_keys() -> dict:
    """Читает .keys и возвращает словарь с uuid, shortsid, PrivateKey, PublicKey и т.п."""
    if not os.path.exists(KEYS_PATH):
        print(f"Файл ключей не найден: {KEYS_PATH}")
        sys.exit(1)

    keys = {}
    with open(KEYS_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if not line or ":" not in line:
                continue
            k, v = line.split(":", 1)
            keys[k.strip()] = v.strip()
    return keys


def restart_xray() -> None:
    run("systemctl restart xray")


def get_users(cfg: dict):
    return cfg["inbounds"][0]["settings"]["clients"]


def user_list():
    cfg = load_config()
    clients = get_users(cfg)
    if not clients:
        print("Список клиентов пуст")
        return False
    print(f"Всего пользователей: {len(clients)}")
    for i, c in enumerate(clients, start=1):
        print(f"{i}. {c.get('email', 'no-email')}")
    return len(clients)

def add_user_interactive() -> None:
    email = input("Введите имя пользователя (email): ").strip()
    if not email or " " in email:
        print("Имя пользователя не может быть пустым или содержать пробелы.")
        return

    cfg = load_config()
    clients = get_users(cfg)

    if any(c.get("email") == email for c in clients):
        print("Пользователь с таким именем уже существует.")
        return

    uuid = run("xray uuid")
    clients.append({
        "email": email,
        "id": uuid,
        "flow": "xtls-rprx-vision"
    })
    cfg["inbounds"][0]["settings"]["clients"] = clients
    save_config(cfg)
    restart_xray()
    print(f"Пользователь {email} успешно добавлен.")
    print()
    make_link_for_email(email)


def remove_user_interactive() -> bool:
    cfg = load_config()
    clients = get_users(cfg)
    if not clients:
        print("Нет клиентов для удаления.")
        return False

    print("Список клиентов:")
    for i, c in enumerate(clients, start=1):
        print(f"{i}. {c.get('email', 'no-email')}")

    choice = input("Введите номер клиента для удаления: ").strip()
    if not choice.isdigit():
        print("Ошибка: нужно ввести число.")
        return False
    idx = int(choice)
    if idx < 1 or idx > len(clients):
        print(f"Ошибка: номер должен быть от 1 до {len(clients)}")
        return False

    email = clients[idx - 1].get("email", "no-email")
    del clients[idx - 1]
    cfg["inbounds"][0]["settings"]["clients"] = clients
    save_config(cfg)
    restart_xray()
    print(f"Клиент {email} удалён.")
    return True


def remove_user_for_email(email: str) -> bool:
    cfg = load_config()
    clients = get_users(cfg)

    if not clients:
        print("Нет клиентов для удаления.")
        return False

    # Ищем клиента с нужным email в списке
    found = False
    for i, client in enumerate(clients):
        if client.get("email") == email:
            # Удаляем найденного клиента из списка
            del clients[i]
            found = True
            break

    if not found:
        print(f"Клиент с email '{email}' не найден.")
        return False

    # Обновляем конфиг и сохраняем
    cfg["inbounds"][0]["settings"]["clients"] = clients
    save_config(cfg)
    restart_xray()

    print(f"Клиент {email} успешно удалён.")
    return True


def make_link_for_email(email: str):
    """Создаёт ссылку и QR-код для пользователя по email."""
    cfg = load_config()
    keys = load_keys()

    clients = get_users(cfg)
    user = None
    for c in clients:
        if c.get("email") == email:
            user = c
            break

    if user is None:
        print("Пользователь не найден.")
        return

    protocol = cfg["inbounds"][0]["protocol"]
    port = cfg["inbounds"][0]["port"]
    uuid = user["id"]
    pbk = keys.get("Password", keys.get("PublicKey", ""))  # на случай другого формата
    sid = keys.get("shortsid", "")
    sni = cfg["inbounds"][0]["streamSettings"]["realitySettings"]["serverNames"][0]
    ip = run("curl -4 -s icanhazip.com")

    link = (
        f"{protocol}://{uuid}@{ip}:{port}"
        f"?security=reality&sni={sni}&fp=firefox&pbk={pbk}"
        f"&sid={sid}&spx=/&type=tcp&flow=xtls-rprx-vision&encryption=none#{email}"
    )

    print()
    print("Ссылка для подключения:")
    print(link)
    print()
    print("QR-код:")
    # qrencode должен быть установлен
    subprocess.run(f'echo "{link}" | qrencode -t ansiutf8', shell=True)
    return link


def make_link_mainuser() -> None:
    """Ссылка для основного пользователя (email = main)."""
    make_link_for_email("main")


def sharelink_interactive() -> None:
    """Выбрать пользователя из списка и сгенерировать ссылку + QR."""
    cfg = load_config()
    clients = get_users(cfg)
    if not clients:
        print("Список клиентов пуст.")
        return

    emails = [c.get("email", "no-email") for c in clients]
    print("Список клиентов:")
    for i, e in enumerate(emails, start=1):
        print(f"{i}. {e}")

    choice = input("Выберите клиента: ").strip()
    if not choice.isdigit():
        print("Ошибка: нужно ввести число.")
        return
    idx = int(choice)
    if idx < 1 or idx > len(emails):
        print(f"Ошибка: номер должен быть от 1 до {len(emails)}")
        return

    email = emails[idx - 1]
    make_link_for_email(email)


def menu() -> None:
    while True:
        print("\n==== Xray User Manager ====")
        print("1) Показать список пользователей")
        print("2) Добавить пользователя")
        print("3) Удалить пользователя")
        print("4) Ссылка/QR для основного пользователя (main)")
        print("5) Ссылка/QR для выбранного пользователя")
        print("0) Выход")
        choice = input("Выберите действие: ").strip()

        if choice == "1":
            user_list()
        elif choice == "2":
            add_user_interactive()
        elif choice == "3":
            remove_user_interactive()
        elif choice == "4":
            make_link_mainuser()
        elif choice == "5":
            sharelink_interactive()
        elif choice == "0":
            break
        else:
            print("Неверный выбор.")


if __name__ == "__main__":
    # Если хотите использовать аргументы CLI, можно расширить через argparse,
    # но сейчас по умолчанию запускается меню.
    menu()
