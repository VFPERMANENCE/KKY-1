import argparse
import re
from pathlib import Path
from urllib.parse import urlparse

def validate_package_name(value):
    if not value.strip():
        raise argparse.ArgumentTypeError("Имя пакета не может быть пустым.")
    return value

def validate_url_or_path(value):
    parsed = urlparse(value)
    if parsed.scheme in ("http", "https"):
        return value
    p = Path(value)
    return str(p.absolute()) #Проверка будет в TestRepository

def validate_mode(value):
    allowed = ["local", "remote", "test"]
    if value not in allowed:
        raise argparse.ArgumentTypeError(f"Режим '{value}' не поддерживается. Используйте: {', '.join(allowed)}.")
    return value

def validate_version(value):
    if not value.strip():
        raise argparse.ArgumentTypeError("Версия пакета не может быть пустой.")
    if not re.match(r"^\d+(\.\d+){0,2}([_-]\w+)*$", value):#регулярка
        raise argparse.ArgumentTypeError("Версия должна быть в формате X.Y или X.Y.Z (например, 1.0.3 или 1.2.3-r0).")
    return value

def validate_output(value):
    if not value.strip():
        raise argparse.ArgumentTypeError("Имя выходного файла не может быть пустым.")
    if not any(value.endswith(ext) for ext in [".png", ".jpg", ".svg"]):
        raise argparse.ArgumentTypeError("Имя выходного файла должно оканчиваться на .png, .jpg или .svg.")
    return value