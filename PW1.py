import argparse
import shlex
import sys
import os
import tkinter as tk
from tkinter import scrolledtext
from datetime import datetime, timezone # Добавлен timezone для исправления DeprecationWarning
import csv
import hashlib
import base64


class VFSNode: #Представляет файл или директорию в VFS.
    def __init__(self, name, type='dir', content=None):
        self.name = name
        self.type = type
        self.content = content # содержимое (Base64 для файлов)
        self.children = {}      # только для директорий


class VFS: #Виртуальная файловая система, хранящаяся в памяти.
    def __init__(self, name="Unnamed VFS"):
        self.name = name
        self.root = VFSNode("/", 'dir')
        self.current_dir = self.root
        self.hash_value = "" # SHA-256 хеш данных
        self.raw_data_string = "" # Исходная строка данных для хеширования

    def calculate_hash(self): #Вычисляет SHA-256 хеш всех данных VFS (для команды vfs-info).
        # Хешируем исходную строку данных CSV
        self.hash_value = hashlib.sha256(self.raw_data_string.encode('utf-8')).hexdigest()
        return self.hash_value

    def get_node(self, path): #Возвращает VFSNode по абсолютному или относительному пути.
        # Упрощенная реализация: поддержка только абсолютных путей или имен
        if path == "/":
            return self.root
        
        path_parts = [p for p in path.split('/') if p]

        current_node = self.root
        
        for part in path_parts:
            if part in current_node.children:
                current_node = current_node.children[part]
            else:
                return None
        
        return current_node
    
    def get_children(self, node=None): #Возвращает список имен детей для текущего узла или указанного узла.
        node = node or self.current_dir
        if node.type != 'dir':
            return None
        return sorted(node.children.keys())


def load_vfs_from_csv(file_path): #Загружает VFS из CSV-файла.Возвращает (VFS_object, error_message).
    
    vfs_name = os.path.basename(file_path)
    vfs = VFS(name=vfs_name)
    raw_data_list = [] # Список строк для последующего хеширования
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            vfs.raw_data_string = content # Сохраняем все содержимое для хеширования
            
            # Чтение CSV, включая заголовки
            reader = csv.reader(content.splitlines(), delimiter=',')
            header = next(reader) # Пропускаем заголовок

            if header != ['Type', 'Path', 'Content']:
                 return None, "Неверный формат заголовка CSV: ожидается ['Type', 'Path', 'Content']"

            for row in reader:
                if len(row) != 3:
                    return None, f"Неверное количество столбцов в строке: {row}"
                
                # Удаляем BOM, если присутствует
                row = [item.lstrip('\ufeff') for item in row]
                
                vfs_type, vfs_path, vfs_content = [r.strip() for r in row]

                if not vfs_path.startswith('/'):
                    return None, f"Путь '{vfs_path}' должен начинаться с '/'"
                
                # Разбираем путь
                path_parts = [p for p in vfs_path.split('/') if p]
                filename = path_parts[-1] if path_parts else '/'
                parent_parts = path_parts[:-1]
                
                current_node = vfs.root
                
                # Строим путь к родительской папке
                for part in parent_parts:
                    if part not in current_node.children or current_node.children[part].type != 'dir':
                        # Создаем отсутствующие промежуточные директории
                        new_node = VFSNode(part, 'dir')
                        current_node.children[part] = new_node
                    current_node = current_node.children[part]
                
                # Добавляем конечный элемент
                if vfs_type == 'dir':
                    if filename not in current_node.children:
                         current_node.children[filename] = VFSNode(filename, 'dir')
                    # Если папка уже создана (как промежуточный узел), просто игнорируем
                elif vfs_type == 'file':
                    if filename in current_node.children:
                        return None, f"Элемент '{filename}' уже существует в VFS"
                    
                    try:
                        # Декодирование содержимого для проверки корректности base64
                        base64.b64decode(vfs_content)
                        current_node.children[filename] = VFSNode(filename, 'file', vfs_content)
                    except Exception:
                         return None, f"Неверный формат Base64 для файла: {filename}"
                else:
                    return None, f"Неверный тип VFS: {vfs_type}"

    except FileNotFoundError:
        return None, f"Ошибка загрузки VFS: Файл '{file_path}' не найден."
    except Exception as e:
        return None, f"Ошибка загрузки VFS: Неверный формат данных CSV: {e}"

    # После успешной загрузки вычисляем хеш
    vfs.calculate_hash()
    return vfs, None


class VFSConfig: #все внутренние настройки
    def __init__(self, root_path=None, startup_script=None, vfs_file=None):
        self.root_path = root_path or os.getcwd()
        self.startup_script = startup_script
        # ИСПРАВЛЕНИЕ: Используем timezone-aware datetime
        self.start_time = datetime.now(timezone.utc).isoformat()
        self.vfs_file = vfs_file
        self.vfs = None # Объект VFS будет загружен в main()

        # Текущий путь в VFS (для cd/ls)
        self.vfs_cwd = "/" 
        
    def items(self):
        # Добавляем информацию о VFS в конфигурацию
        vfs_info = self.vfs.name if self.vfs else "None (Not Loaded)"
        vfs_hash = self.vfs.hash_value if self.vfs else "N/A"

        return {
            "vfs_root_os": self.root_path,
            "startup_script": self.startup_script,
            "vfs_file": self.vfs_file,
            "vfs_loaded_name": vfs_info,
            "vfs_data_hash_sha256": vfs_hash,
            "vfs_current_dir": self.vfs_cwd,
            "start_time_utc": self.start_time,
            "argv": " ".join(sys.argv)
        }.items()

def parse_command(line): #Парсер команд с поддержкой кавычек (shlex). Возвращает список токенов.
    try:
        tokens = shlex.split(line)
    except ValueError as e:
        # Если ошибка парсинга кавычек
        return None, f"parse error: {e}"
    return tokens, None

def act(tokens, config: VFSConfig): #Выполняет заглушки команд. Принимает уже распарсенные токены (list) и config. Возвращает (output_str, is_error_bool).
    if tokens is None:
        return "parse error", True
    if len(tokens) == 0:
        return "", False

    cmd = tokens[0]
    args = tokens[1:]
    
    if not config.vfs and cmd not in ("exit", "conf-dump"):
        return f"VFS не загружена. Доступны только exit и conf-dump.", True
    
    current_node = config.vfs.get_node(config.vfs_cwd) if config.vfs else None

    if cmd == "exit":
        return "exit", False
    
    elif cmd == "vfs-info":
        if not config.vfs:
             return "VFS-INFO: Виртуальная ФС не загружена.", True
        
        output = [
            f"VFS Name: {config.vfs.name}",
            f"SHA-256 Hash: {config.vfs.hash_value}",
            f"Root Path: {config.vfs_cwd}"
        ]
        return "\n".join(output), False
        
    elif cmd == "ls":
        if current_node is None or current_node.type != 'dir':
            return f"ls: {config.vfs_cwd}: Directory not found or is a file.", True
        
        if len(args) > 0:
            # Упрощенная заглушка для ls с аргументами: просто выводим имя
            target_path = os.path.join(config.vfs_cwd, args[0])
            target_node = config.vfs.get_node(target_path)
            
            if target_node:
                return f"{target_node.name} ({target_node.type})", False
            else:
                 return f"ls: {args[0]}: No such file or directory", True


        # Вывод содержимого текущей директории VFS
        lines = []
        for name in config.vfs.get_children():
            node = current_node.children[name]
            type_tag = "[DIR]" if node.type == 'dir' else "[FILE]"
            size = len(node.content) if node.type == 'file' else ""
            lines.append(f"{type_tag} {name} (Size: {size})")
            
        return "\n".join(lines) if lines else "Директория пуста.", False
    
    elif cmd == "cd":
        if len(args) == 0:
            config.vfs_cwd = "/"
            return "", False

        target = args[0]
        
        # Обработка ".." (наивно)
        if target == "..":
            if config.vfs_cwd == "/":
                return "", False # Остаемся в корне
            
            # Убираем последний сегмент
            parent_path = os.path.dirname(config.vfs_cwd)
            # os.path.dirname('/data/docs') -> /data
            # os.path.dirname('/data') -> /
            config.vfs_cwd = parent_path if parent_path else "/"
            return "", False
        
        # Формируем целевой путь
        if target.startswith('/'):
            # Абсолютный путь
            new_path = target
        else:
            # Относительный путь
            new_path = os.path.join(config.vfs_cwd, target)
            
        # Нормализация пути (убираем двойные слэши и т.п.)
        new_path = os.path.normpath(new_path)
        # Если нормализованный путь — только точка, считаем текущей директорией
        if new_path == '.': new_path = config.vfs_cwd

        target_node = config.vfs.get_node(new_path)
        
        if target_node is None or target_node.type != 'dir':
            return f"cd: {target}: No such directory in VFS or is a file", True
        
        # Успешная смена директории
        config.vfs_cwd = new_path
        return "", False
        
    elif cmd == "conf-dump":
        lines = []
        # Теперь выводим vfs_current_dir, который обновляется командой cd
        for k, v in config.items():
            lines.append(f"{k}={v}")
        return "\n".join(lines), False
        
    else:
        return f"{cmd}: command not found", True



class VFSApp:
    def __init__(self, config: VFSConfig): #создаем само окно
        self.config = config
        self.root = tk.Tk()
        self.root.title("VFS Shell (Stage 3)")
        self.root.geometry("800x600")

        # Добавим отображение текущей директории VFS
        self.cwd_label = tk.Label(self.root, text=f"CWD: {self.config.vfs_cwd}", anchor='w')
        self.cwd_label.pack(padx=10, pady=(10, 0), fill=tk.X)
        
        self.output_text = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, height=20, width=70)
        self.output_text.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        self.output_text.config(state=tk.NORMAL)

        self.entry = tk.Entry(self.root, width=70)
        self.entry.pack(padx=10, pady=5, fill=tk.X)
        self.entry.bind("<Return>", self.execute_command)

        self.send_button = tk.Button(self.root, text="Отправить", command=self.execute_command)
        self.send_button.pack(pady=5)

        self.entry.focus()
        self._should_exit = False

    def update_cwd_label(self): #Обновляет метку текущей директории в GUI.
         self.cwd_label.config(text=f"CWD: {self.config.vfs_cwd}")
        
    def writeln(self, text=""): #Вставляет текст в output_text и скроллит вниз.
        self.output_text.insert(tk.END, text + "\n")
        self.output_text.see(tk.END)
        self.root.update()

    def execute_command(self, event=None):
        command_str = self.entry.get().strip()
        if command_str == "" and event is not None:
            return ""
        
        # Обновляем метку CWD перед выводом (чтобы увидеть, если cd изменит путь)
        self.update_cwd_label()
        self.writeln(f"vfs:{self.config.vfs_cwd}$ {command_str}")
        tokens, perr = parse_command(command_str)
        
        if perr:
            self.writeln(f"parse error: {perr}")
            self.entry.delete(0, tk.END)
            return

        output, is_error = act(tokens, self.config)
        
        if output == "exit" and not is_error:
            self.writeln("Exiting emulator...")
            self._should_exit = True
            self.root.quit()
            return
        
        if output:
            self.writeln(output)
        
        if tokens and tokens[0] == "cd":
            # Принудительно обновляем метку после успешного cd
            self.update_cwd_label()

        self.entry.delete(0, tk.END)

    def run_startup_script(self):# Если указан startup_script, выполняем его построчно.
        sp = self.config.startup_script
        if not sp:
            return

        # Попытка открыть скрипт (может быть относительный путь)
        try:
            with open(sp, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception as e:
            self.writeln(f"failed to open startup script '{sp}': {e}")
            return

        self.writeln(f"--- Running startup script: {sp} ---")
        for raw_line in lines:
            line = raw_line.rstrip("\n")
            # пропускаем пустые строки и комментарии (начинаются с #)
            if line.strip() == "" or line.strip().startswith("#"):
                continue

            self.writeln(f"vfs:{self.config.vfs_cwd}$ {line}")
            tokens, perr = parse_command(line)
            if perr:
                self.writeln(f"parse error: {perr}")
                self.writeln(f"--- Script stopped due to parse error ---")
                return

            output, is_error = act(tokens, self.config)
            if output:
                self.writeln(output)

            if is_error:
                self.writeln(f"--- Script stopped due to error on line: {line} ---")
                return

            if tokens and tokens[0] == "cd":
                 self.update_cwd_label() # Обновляем метку CWD после cd в скрипте

            if tokens and tokens[0] == "exit":
                self.writeln("--- Script requested exit ---")
                return

        self.writeln(f"--- Startup script {sp} finished successfully ---")

    def dump_config_on_start(self): #Отладочный вывод всех параметров при запуске эмулятора (conf-dump style).
        self.writeln("=== Emulator configuration (debug dump) ===")
        for k, v in self.config.items():
            self.writeln(f"{k} = {v}")
        self.writeln("==========================================")
        self.update_cwd_label()

    def start(self, run_script_before_mainloop=True):
        self.dump_config_on_start()
        if run_script_before_mainloop:
            self.run_startup_script()
        self.root.mainloop()

SAMPLE_SCRIPTS = {
    # Скрипт для тестирования VFS
    "test_vfs_full.vfs": """# Тестирование всех реализованных команд (Этап 3)
vfs-info
cd /config
ls
cd ..
ls
cd data/docs
ls
conf-dump
cd /
cd non-existent-dir # Ошибка: остановка скрипта
ls /
""",
    # Скрипт для проверки обработки ошибок VFS
    "test_vfs_errors.vfs": """# Тестирование ошибок и выхода
cd /nonexistent
ls /config/settings.txt # Должна быть ошибка, но ls не поддерживает вывод файлов.
unknown_cmd
exit
""",
    # Скрипт для проверки cd .. и абсолютных путей
     "test_vfs_navigation.vfs": """# Тестирование навигации (cd)
cd /data/docs
vfs-info # Проверка CWD
cd ..
vfs-info # CWD должен стать /data
cd /
vfs-info # CWD должен стать /
exit
"""
}

# Тестовые CSV-файлы для VFS
VFS_CSVS = {
    "vfs_minimal.csv": "Type,Path,Content\ndir,/,",
    "vfs_nested.csv": (
        "Type,Path,Content\n"
        "dir,/config,\n"
        "file,/config/info.txt,VGhpcyBpcyBhIHRlc3QgZmlsZS4=\n"
        "dir,/data,\n"
        "dir,/data/docs,\n"
        "file,/data/docs/report.bin,MDAwMDAwMDAwMA==\n" 
        "file,/readme.md,IyBUaGlzIGlzIHZlcnkgY29vbA==\n"
        "dir,/config/subdir,"
    ),
    "vfs_error.csv": "Type,Path,Content\nfile,/config/settings.txt,invalid base64 content"
}


def create_sample_scripts(path="."):
    created = []
    
    # 1. Создание CSV VFS файлов
    for name, content in VFS_CSVS.items():
        fp = os.path.join(path, name)
        with open(fp, "w", encoding="utf-8") as f:
            f.write(content)
        created.append(fp)
        
    # 2. Создание VFS тестовых скриптов
    for name, content in SAMPLE_SCRIPTS.items():
        fp = os.path.join(path, name)
        with open(fp, "w", encoding="utf-8") as f:
            f.write(content)
        created.append(fp)
        
    return created


def main():
    parser = argparse.ArgumentParser(description="VFS Emulator (stage 3)")
    parser.add_argument("--vfs-root", dest="vfs_root", help="Path to physical location of OS root", default=os.getcwd())
    parser.add_argument("--startup-script", dest="startup_script", help="Path to startup script to execute at launch")
    parser.add_argument("--vfs-file", dest="vfs_file", help="Path to VFS CSV file to load")
    parser.add_argument("--create-samples", action="store_true", help="Create sample scripts and VFS CSVs in current directory and exit")
    args = parser.parse_args()

    if args.create_samples:
        created = create_sample_scripts(".")
        print("Created sample scripts and VFS CSV files:")
        for c in created:
            print("   ", c)
        print("\nRun emulator with --vfs-file <one_of_the_csvs> --startup-script <one_of_the_scripts> to test.")
        return

    # 1. Инициализация конфигурации
    config = VFSConfig(root_path=args.vfs_root, startup_script=args.startup_script, vfs_file=args.vfs_file)
    
    # 2. Загрузка VFS 
    if args.vfs_file:
        vfs, vfs_error = load_vfs_from_csv(args.vfs_file)
        if vfs_error:
            # Выводим ошибку загрузки VFS в консоль и выходим
            print(f"FATAL VFS LOAD ERROR: {vfs_error}")
            sys.exit(1)
        config.vfs = vfs
        
    # 3. Проверка, что VFS была загружена, если не загружена, то доступны только exit и conf-dump 
    if not config.vfs and config.vfs_file:
         print("FATAL VFS LOAD ERROR: VFS file specified but failed to load. Exiting.")
         sys.exit(1)
         
    # 4. Создаём и запускаем GUI-приложение
    app = VFSApp(config)
    app.start(run_script_before_mainloop=True)

if __name__ == "__main__":
    main()
