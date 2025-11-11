import argparse
import sys
from urllib.parse import urlparse
from urllib.parse import urljoin
from pathlib import Path
import tarfile
import gzip
import urllib.request

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
    if not re.match(r"^\d+(\.\d+){0,2}([_-]\w+)*$", value): #регулярка - ^начало строки, \d+ одна или больше цифр,(\.\d+)точка + одна или больше цифр,{0,2}может поторяться с 0 до 2х раз,([_-]\w+)*для суффиксов версий,$-конец строки
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

def get_apk_path(repo_url, package, version, mode, dest_dir="downloads"):
    apk_name = f"{package}-{version}.apk"
    Path(dest_dir).mkdir(exist_ok=True)

    if mode == "remote":
        apk_url = urljoin(repo_url, apk_name) #######!!!
        apk_path = Path(dest_dir) / apk_name
        print(f"Скачивание {apk_url} ...")
        try:
            urllib.request.urlretrieve(apk_url, apk_path)
        except Exception as e:
            raise RuntimeError(f"Не удалось скачать пакет: {e}")
        if not apk_path.exists() or apk_path.stat().st_size == 0:
            raise RuntimeError("Файл не скачался или пуст.")
        print(f" Скачано: {apk_path}")
    else:  # local
        apk_path = Path(repo_url) / apk_name
        if not apk_path.exists():
            raise RuntimeError(f"Файл {apk_path} не найден локально.")
        print(f"Используется локальный файл: {apk_path}")

    return apk_path

def extract_control_file(apk_path):
    """Извлекает данные пакета (control, +PKGINFO или .PKGINFO) из .apk."""
    with tarfile.open(apk_path, "r:gz") as tar:
        members = tar.getmembers()
        print("Содержимое архива:")
        for m in members:
            print(" -", m.name)

         # Ищем .PKGINFO (основной файл метаданных в Alpine)
        for member in members:
            if member.name == ".PKGINFO":
                print("Найден .PKGINFO файл")
                f = tar.extractfile(member)
                content = f.read().decode("utf-8", errors="ignore")
                return content
            
        # Ищем control.tar.gz или control.tar
        for member in members:
            if member.name.endswith(("control.tar.gz", "control.tar")):
                print(f"Найден архив control: {member.name}")
                control_tar = tar.extractfile(member)
                if control_tar is None:
                    continue

                import io
                with tarfile.open(fileobj=io.BytesIO(control_tar.read())) as control_inner:
                    for sub in control_inner.getmembers():
                        if sub.name == "control":
                            f = control_inner.extractfile(sub)
                            content = f.read().decode("utf-8", errors="ignore")
                            print("Извлечен control файл")
                            return content

    raise RuntimeError("Файл control или +PKGINFO/.PKGINFO не найден в архиве.")

def parse_dependencies(control_text):
    """Находит и возвращает список зависимостей из control или похожего по смыслу файла."""
    """Возвращает список зависимостей из строки depends = ... в .PKGINFO/.control."""
    dependencies = []
    
    print("\nАнализ данных пакета...")
    print("Содержимое .PKGINFO:")
    print("-" * 10)
    print(control_text)
    print("-" * 10)
    
    for line in control_text.splitlines():
        line = line.strip()
        
        # Зависимости в Alpine .PKGINFO
        if line.startswith("depend = "):
            dep = line.split("=", 1)[1].strip()
            if dep and dep not in dependencies:
                dependencies.append(dep)
                print(f"Найдена зависимость: {dep}")
    
    return dependencies
def display_dependencies(package, version, dependencies, ascii_mode=False, filter_str=None):
    """Отображает зависимости в указанном формате"""
    
    # ФИЛЬТР 
    if filter_str:
        original_count = len(dependencies)
        dependencies = [dep for dep in dependencies if filter_str.lower() in dep.lower()]
        print(f"\nПрименен фильтр '{filter_str}': показано {len(dependencies)} из {original_count} зависимостей")
    
    if not dependencies:
        print(f"\nЗависимости не найдены (возможно, пакет не имеет зависимостей или фильтр не нашёл совпадений).")
        return
    
    print(f"\nПрямые зависимости пакета {package}-{version}:")
    print(f"Всего найдено: {len(dependencies)}")
    
    if ascii_mode:
        print("┌─ Зависимости")
        for i, dep in enumerate(dependencies):
            if i == len(dependencies) - 1:
                print(f"└── {dep}")
            else:
                print(f"├── {dep}")
    else:
        for i, dep in enumerate(dependencies, 1):
            print(f"  {i:2d}. {dep}")


def main():
    parser = argparse.ArgumentParser (
        description="Инструмент визуализации графа зависимостей",
        epilog="Пример: python second.py --package-name numpy --repo-url https://example.com/repo --mode local --version 1.0 --output graph.png"
    )
    
    parser.add_argument("--package-name", required=True, help="Имя анализируемого пакета.")
    parser.add_argument("--repo-url", required=True, type=validate_url_or_path,
                        help="URL репозитория или путь к тестовому репозиторию.")
    parser.add_argument("--mode", required=True, type=validate_mode,
                        help="Режим работы с тестовым репозиторием (local или remote).")
    parser.add_argument("--version", required=True, help="Версия анализируемого пакета.")
    parser.add_argument("--output", required=False, help="Имя выходного файла для графа (например, graph.png).")
    parser.add_argument("--ascii", action="store_true", help="Режим вывода зависимостей в ASCII-дереве.")
    parser.add_argument("--filter", help="Подстрока для фильтрации пакетов.")
    
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()
    
    try:
        print(f"\n Анализ пакета: {args.package_name} ({args.version})")
        print(f"Репозиторий/путь: {args.repo_url}")
        print(f"Режим работы: {args.mode}")
        
        # 1. Скачать пакет
        apk_path = get_apk_path(args.repo_url, args.package_name, args.version, args.mode)

        # 2. Извлечь control файл
        control_data = extract_control_file(apk_path)

        # 3. Распарсить зависимости
        deps = parse_dependencies(control_data)

        # 4. Вывести результат
        display_dependencies(args.package_name, args.version, deps, 
                           args.ascii, args.filter)
    except Exception as e:
        print(f" Ошибка: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

# #  Без фильтра (все зависимости)
# python second.py --package-name busybox --repo-url https://dl-cdn.alpinelinux.org/alpine/v3.21/main/x86_64/ --mode remote --version 1.37.0-r13

# #  С фильтром "so" (только библиотеки)
# python second.py --package-name busybox --repo-url https://dl-cdn.alpinelinux.org/alpine/v3.21/main/x86_64/ --mode remote --version 1.37.0-r13 --filter so

# # С фильтром "lib" 
# python second.py --package-name busybox --repo-url https://dl-cdn.alpinelinux.org/alpine/v3.21/main/x86_64/ --mode remote --version 1.37.0-r13 --filter lib

# # С ASCII-выводом и фильтром
# python second.py --package-name busybox --repo-url https://dl-cdn.alpinelinux.org/alpine/v3.21/main/x86_64/ --mode remote --version 1.37.0-r13 --ascii --filter so