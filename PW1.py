import argparse
import shlex
import sys
import os
import tkinter as tk
from tkinter import scrolledtext
from datetime import datetime

class VFSConfig: #все внутренние настройки
    def __init__(self, root_path=None, startup_script=None):
        self.root_path = root_path or os.getcwd()
        self.startup_script = startup_script
        self.start_time = datetime.utcnow().isoformat() + "Z"

    def items(self):
        return {
            "vfs_root": self.root_path,
            "startup_script": self.startup_script,
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

def act(tokens, config): #Выполняет заглушки команд.Принимает уже распарсенные токены (list) и config.Возвращает (output_str, is_error_bool).
    if tokens is None:
        return "parse error", True
    if len(tokens) == 0:
        return "", False

    cmd = tokens[0]
    args = tokens[1:]

    if cmd == "exit":
        return "exit", False  # GUI обработает выход отдельно
    elif cmd == "ls":
        # просто покажем аргументы
        return f"ls {' '.join(args)}", False
    elif cmd == "cd":
        # попробуем сделать простую проверку на существование пути в конфиге root
        if len(args) == 0:
            return "cd: missing operand", True
        target = args[0]
        # относительный путь от vfs root
        full = os.path.join(config.root_path, target)
        if os.path.exists(full):
            return f"cd {target}", False
        else:
            return f"cd: {target}: No such file or directory", True
    elif cmd == "conf-dump":
        # формат ключ=значение
        lines = []
        for k, v in config.items():
            lines.append(f"{k}={v}")
        return "\n".join(lines), False
    else:
        return f"{cmd}: command not found", True


class VFSApp:
    def __init__(self, config: VFSConfig): #создаем само окно
        self.config = config
        self.root = tk.Tk()
        self.root.title("VFS Shell")
        self.root.geometry("800x600")

        self.output_text = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, height=20, width=70)
        self.output_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        self.output_text.config(state=tk.NORMAL)

        self.entry = tk.Entry(self.root, width=70)
        self.entry.pack(padx=10, pady=5, fill=tk.X)
        self.entry.bind("<Return>", self.execute_command)

        self.send_button = tk.Button(self.root, text="Отправить", command=self.execute_command)
        self.send_button.pack(pady=5)

        self.entry.focus()

        # флаг для выхода из GUI, когда команда exit вызвана
        self._should_exit = False

    def writeln(self, text=""): #Вставляет текст в output_text и скроллит вниз.
        self.output_text.insert(tk.END, text + "\n")
        self.output_text.see(tk.END)
        # принудительно обновим вид, чтобы при выполнении стартового скрипта пользователь видел вывод
        self.root.update()

    def execute_command(self, event=None):
        command_str = self.entry.get().strip()
        if command_str == "" and event is not None:
            return ""  # просто игнорируем пустую строку
        # показать ввод как от пользователя
        self.writeln(f"vfs$ {command_str}")
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

        # показать результат
        if output:
            self.writeln(output)
        else:
            # пустой вывод — всё ок
            pass

        self.entry.delete(0, tk.END)

    def run_startup_script(self):# Если указан startup_script, выполняем его построчно.На экране отображается и ввод, и вывод, имитируя диалог.При первой ошибке — останавливаем выполнение.
        
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
            # пропускаем пустые строки и комментарии 
            if line.strip() == "" or line.strip().startswith("#"):
                continue

            # отображаем как ввод
            self.writeln(f"vfs$ {line}")
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

            # если команда exit — прекращаем скрипт исполнения
            if tokens and tokens[0] == "exit":
                self.writeln("--- Script requested exit ---")
                return

        self.writeln(f"--- Startup script {sp} finished successfully ---")

    def dump_config_on_start(self): #Отладочный вывод всех параметров при запуске эмулятора (conf-dump style).
        self.writeln("=== Emulator configuration (debug dump) ===")
        for k, v in self.config.items():
            self.writeln(f"{k} = {v}")
        self.writeln("==========================================")

    def start(self, run_script_before_mainloop=True):
        self.dump_config_on_start()
        if run_script_before_mainloop:
            self.run_startup_script()
        # запускаем GUI
        self.root.mainloop()

SAMPLE_SCRIPTS = {
    "sample_ok.vfs": """# Пример корректного скрипта
conf-dump
ls "my folder"
cd existing_dir
""",
    "sample_error.vfs": """# Скрипт с ошибкой: неверная команда -> остановка
ls
unknown_cmd
ls again
""",
    "sample_exit.vfs": """# Скрипт демонстрирующий exit
ls
exit
ls should_not_run
"""
}


def create_sample_scripts(path="."):
    created = []
    for name, content in SAMPLE_SCRIPTS.items():
        fp = os.path.join(path, name)
        with open(fp, "w", encoding="utf-8") as f:
            f.write(content)
        created.append(fp)
    return created


def main():
    parser = argparse.ArgumentParser(description="VFS Emulator (stage 2)")
    parser.add_argument("--vfs-root", dest="vfs_root", help="Path to physical location of VFS (root)", default=os.getcwd())
    parser.add_argument("--startup-script", dest="startup_script", help="Path to startup script to execute at launch")
    parser.add_argument("--create-samples", action="store_true", help="Create sample scripts in current directory and exit")
    args = parser.parse_args()

    if args.create_samples:
        created = create_sample_scripts(".")
        print("Created sample scripts:")
        for c in created:
            print("  ", c)
        print("\nRun emulator with --startup-script <one_of_the_files> to test.")
        return

    config = VFSConfig(root_path=args.vfs_root, startup_script=args.startup_script)

    # Создаём и запускаем GUI-приложение
    app = VFSApp(config)
    app.start(run_script_before_mainloop=True)

if __name__ == "__main__":
    main()
#всё)))
