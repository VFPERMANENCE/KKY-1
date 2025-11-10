import argparse
import sys
from urllib.parse import urlparse
from pathlib import Path

def validate_package_name(value):
    if not value.strip():
        raise argparse.ArgumentTypeError("Имя пакета не может быть пустым.")
    return value

def validate_url_or_path(value):
    parsed = urlparse(value)
    if parsed.scheme in ("http", "https"):
        return value
    p = Path(value)
    if not p.exists():
        raise argparse.ArgumentTypeError(f"'{value}' не является корректным URL или путём к файлу.")
    return str(p.resolve())

def validate_mode(value):
    allowed = ["local", "remote"]
    if value not in allowed:
        raise argparse.ArgumentTypeError(f"Режим '{value}' не поддерживается. Используйте: {', '.join(allowed)}.")
    return value

def validate_version(value):
    if not value.strip():
        raise argparse.ArgumentTypeError("Версия пакета не может быть пустой.")
    # простейшая валидация вроде X.Y.Z
    import re
    if not re.match(r"^\d+(\.\d+){0,2}$", value): #регулярка - ^начало строки, \d+ одна или больше цифр,(\.\d+)
        raise argparse.ArgumentTypeError("Версия должна быть в формате X.Y или X.Y.Z (например, 1.0.3).")
    return value

def validate_output(value):
    if not value.strip():
        raise argparse.ArgumentTypeError("Имя выходного файла не может быть пустым.")
    if not any(value.endswith(ext) for ext in [".png", ".jpg", ".svg"]):
        raise argparse.ArgumentTypeError("Имя выходного файла должно оканчиваться на .png, .jpg или .svg.")
    return value

def validate_filter(value):
    if not isinstance(value, str):
        raise argparse.ArgumentTypeError("Фильтр должен быть строкой.")
    return value

def parse_args():
    parser = argparse.ArgumentParser (
        description="Инструмент визуализации графа зависимостей",
        epilog="Пример: python depgraph.py --package-name numpy --repo-url ./repo --mode local --version 1.0 --output graph.png"
    )
    
    parser.add_argument("--package-name", required=True, help="Имя анализируемого пакета.")
    parser.add_argument("--repo-url", required=True, type=validate_url_or_path,
                        help="URL репозитория или путь к тестовому репозиторию.")
    parser.add_argument("--mode", required=True, type=validate_mode,
                        help="Режим работы с тестовым репозиторием (local или remote).")
    parser.add_argument("--version", required=True, help="Версия анализируемого пакета.")
    parser.add_argument("--output", required=True, help="Имя выходного файла для графа (например, graph.png).")
    parser.add_argument("--ascii", action="store_true", help="Режим вывода зависимостей в ASCII-дереве.")
    parser.add_argument("--filter", help="Подстрока для фильтрации пакетов.")
    
    if len(sys.argv) == 1: parser.print_help() 
    sys.exit(1)
    
    return parser.parse_args()

def main():
    try:
        args = parse_args()

        # Вывод конфигурации
        print("Параметры конфигурации:")
        for key, value in vars(args).items():
            print(f"{key} = {value}")

    except argparse.ArgumentTypeError as e:
        print(f"Ошибка в параметрах: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Неожиданная ошибка: {e}", file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    main()
