import argparse
import sys
from urllib.parse import urlparse
from pathlib import Path

def validate_url_or_path(value):
    """Проверка: значение должно быть либо корректным URL, либо существующим путем."""
    parsed = urlparse(value)
    if parsed.scheme in ("http", "https"):
        return value
    p = Path(value)
    if not p.exists():
        raise argparse.ArgumentTypeError(f"Путь '{value}' не существует.")
    return str(p.resolve())

def validate_mode(value):
    allowed = ["local", "remote"]
    if value not in allowed:
        raise argparse.ArgumentTypeError(f"Режим '{value}' не поддерживается. Используйте {allowed}.")
    return value

def parse_args():
    parser = argparse.ArgumentParser(
        description="Инструмент визуализации графа зависимостей (этап 1: конфигурация)"
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
