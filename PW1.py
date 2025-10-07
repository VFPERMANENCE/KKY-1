import argparse
import shlex
import sys
import os
import tkinter as tk
from tkinter import scrolledtext
from datetime import datetime, timezone
import csv
import hashlib
import base64
from typing import Tuple, Optional, List
import binascii


class VFSNode:
    def __init__(self, name: str, type: str = 'dir', content: Optional[str] = None):
        self.name = name
        self.type = type
        self.content = content
        self.children = {}


class VFS:
    def __init__(self, name: str = "Unnamed VFS"):
        self.name = name
        self.root = VFSNode("/", 'dir')
        self.current_dir = self.root
        self.hash_value = ""
        self.raw_data_string = ""

    def calculate_hash(self):
        self.hash_value = hashlib.sha256(self.raw_data_string.encode('utf-8')).hexdigest()
        return self.hash_value

    def get_node(self, path: str) -> Optional[VFSNode]:
        if path == "" or path == "/":
            return self.root

        path_parts = [p for p in path.strip('/').split('/') if p]
        current_node = self.root

        for part in path_parts:
            if current_node.type != 'dir':
                return None
            if part in current_node.children:
                current_node = current_node.children[part]
            else:
                return None

        return current_node

    def get_children(self, node: Optional[VFSNode] = None) -> Optional[List[str]]:
        node = node or self.current_dir
        if node.type != 'dir':
            return None
        return sorted(node.children.keys())


def load_vfs_from_csv(file_path: str) -> Tuple[Optional[VFS], Optional[str]]:
    vfs_name = os.path.basename(file_path)
    vfs = VFS(name=vfs_name)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            vfs.raw_data_string = content

            reader = csv.reader(content.splitlines(), delimiter=',')

            try:
                header = next(reader)
            except StopIteration:
                return None, f"Ошибка загрузки VFS: Файл '{file_path}' пуст."

            if header != ['Type', 'Path', 'Content']:
                return None, "Неверный формат заголовка CSV: ожидается ['Type', 'Path', 'Content']"

            for row in reader:
                if len(row) != 3:
                    return None, f"Неверное количество столбцов в строке: {row}"

                row = [item.lstrip('\ufeff') for item in row]
                vfs_type, vfs_path, vfs_content = [r.strip() for r in row]

                if not vfs_path.startswith('/'):
                    return None, f"Путь '{vfs_path}' должен начинаться с '/'"

                path_parts = [p for p in vfs_path.split('/') if p]
                filename = path_parts[-1] if path_parts else '/'
                parent_parts = path_parts[:-1]

                current_node = vfs.root
                for part in parent_parts:
                    if part not in current_node.children or current_node.children[part].type != 'dir':
                        new_node = VFSNode(part, 'dir')
                        current_node.children[part] = new_node
                    current_node = current_node.children[part]

                if vfs_type == 'dir':
                    if filename not in current_node.children:
                        current_node.children[filename] = VFSNode(filename, 'dir')
                elif vfs_type == 'file':
                    if filename in current_node.children:
                        return None, f"Элемент '{filename}' уже существует в VFS"

                    try:
                        decoded_bytes = base64.b64decode(vfs_content)
                        decoded_bytes.decode('utf-8')
                        current_node.children[filename] = VFSNode(filename, 'file', vfs_content)
                    except binascii.Error:
                        return None, f"Неверный формат Base64 для файла (ошибка binascii): {filename}"
                    except UnicodeDecodeError:
                        return None, f"Неверный формат Base64 для файла (ошибка кодирования): {filename}"
                else:
                    return None, f"Неверный тип VFS: {vfs_type}"

    except FileNotFoundError:
        return None, f"Ошибка загрузки VFS: Файл '{file_path}' не найден."
    except Exception as e:
        return None, f"Ошибка загрузки VFS: Неверный формат данных CSV: {e}"

    vfs.calculate_hash()
    return vfs, None


class VFSConfig:
    def __init__(self, root_path: Optional[str] = None, startup_script: Optional[str] = None, vfs_file: Optional[str] = None):
        self.root_path = root_path or os.getcwd()
        self.startup_script = startup_script
        self.start_time = datetime.now(timezone.utc).isoformat()
        self.vfs_file = vfs_file
        self.vfs: Optional[VFS] = None
        self.vfs_cwd = "/"

    def items(self):
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


def parse_command(line: str) -> Tuple[Optional[List[str]], Optional[str]]:
    try:
        tokens = shlex.split(line)
    except ValueError as e:
        return None, f"parse error: {e}"
    return tokens, None


def act(tokens: List[str], config: VFSConfig) -> Tuple[str, bool]:
    if tokens is None:
        return "parse error", True
    if len(tokens) == 0:
        return "", False

    cmd = tokens[0]
    args = tokens[1:]

    if not config.vfs and cmd not in ("exit", "conf-dump"):
        return f"VFS не загружена. Доступны только exit и conf-dump.", True

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
        target_path = config.vfs_cwd
        if len(args) > 0:
            if args[0].startswith('/'):
                target_path = os.path.normpath(args[0])
            elif args[0] == '.':
                target_path = config.vfs_cwd
            elif args[0] == '..':
                target_path = os.path.normpath(os.path.join(config.vfs_cwd, '..'))
            else:
                target_path = os.path.normpath(os.path.join(config.vfs_cwd, args[0]))
            target_path = target_path.replace(os.sep, '/')
            if target_path.startswith('..'):
                target_path = "/"

        current_node = config.vfs.get_node(target_path)
        if current_node is None:
            return f"ls: {target_path}: No such file or directory.", True

        if current_node.type != 'dir':
            return f"[FILE] {current_node.name} (Size: {len(current_node.content)})", False

        lines = []
        for name in current_node.children.keys():
            node = current_node.children[name]
            type_tag = "[DIR]" if node.type == 'dir' else "[FILE]"
            size = len(node.content) if node.type == 'file' and node.content else "N/A"
            lines.append(f"{type_tag} {name} (Size: {size})")
        return "\n".join(sorted(lines)) if lines else "Директория пуста.", False

    elif cmd == "cd":
        if len(args) == 0:
            config.vfs_cwd = "/"
            return "", False

        target = args[0]
        if target.startswith('/'):
            new_path = target
        else:
            new_path = os.path.join(config.vfs_cwd, target)
        new_path = os.path.normpath(new_path).replace(os.sep, '/')
        if new_path.startswith('..'):
            new_path = "/"
        elif new_path == '.':
            new_path = config.vfs_cwd

        target_node = config.vfs.get_node(new_path)
        if target_node is None or target_node.type != 'dir':
            return f"cd: {target}: No such directory in VFS or is a file", True

        config.vfs_cwd = new_path
        return "", False

    elif cmd == "tac":
        if len(args) == 0:
            return "tac: missing operand", True
        target_path = args[0]
        if not target_path.startswith('/'):
            target_path = os.path.join(config.vfs_cwd, target_path)
            target_path = os.path.normpath(target_path).replace(os.sep, '/')
        node = config.vfs.get_node(target_path)
        if node is None or node.type != 'file':
            return f"tac: {target_path}: No such file or not a file.", True
        try:
            content = base64.b64decode(node.content).decode('utf-8')
            lines = content.splitlines()
            lines.reverse()
            return "\n".join(lines), False
        except Exception as e:
            return f"tac: error reading file: {e}", True

    elif cmd == "head":
        if len(args) == 0:
            return "head: missing operand", True
        num_lines = 10
        target_path = args[-1]
        if len(args) >= 3 and args[0] == "-n":
            try:
                num_lines = int(args[1])
            except ValueError:
                return f"head: invalid number of lines: {args[1]}", True
            target_path = args[2]
        if not target_path.startswith('/'):
            target_path = os.path.join(config.vfs_cwd, target_path)
            target_path = os.path.normpath(target_path).replace(os.sep, '/')
        node = config.vfs.get_node(target_path)
        if node is None or node.type != 'file':
            return f"head: {target_path}: No such file or not a file.", True
        try:
            content = base64.b64decode(node.content).decode('utf-8')
            lines = content.splitlines()[:num_lines]
            return "\n".join(lines), False
        except Exception as e:
            return f"head: error reading file: {e}", True

    elif cmd == "uniq":
        if len(args) == 0:
            return "uniq: missing operand", True
        target_path = args[0]
        if not target_path.startswith('/'):
            target_path = os.path.join(config.vfs_cwd, target_path)
            target_path = os.path.normpath(target_path).replace(os.sep, '/')
        node = config.vfs.get_node(target_path)
        if node is None or node.type != 'file':
            return f"uniq: {target_path}: No such file or not a file.", True
        try:
            content = base64.b64decode(node.content).decode('utf-8')
            lines = content.splitlines()
            unique_lines = []
            prev = None
            for line in lines:
                if line != prev:
                    unique_lines.append(line)
                prev = line
            return "\n".join(unique_lines), False
        except Exception as e:
            return f"uniq: error reading file: {e}", True

    elif cmd == "conf-dump":
        lines = []
        for k, v in config.items():
            lines.append(f"{k}={v}")
        return "\n".join(lines), False

    else:
        return f"{cmd}: command not found", True


class VFSApp:
    def __init__(self, config: VFSConfig):
        self.config = config
        self.root = tk.Tk()
        self.root.title("VFS Shell (Stage 4)")
        self.root.geometry("800x600")
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

    def update_cwd_label(self):
        self.cwd_label.config(text=f"CWD: {self.config.vfs_cwd}")

    def writeln(self, text: str = ""):
        self.output_text.insert(tk.END, text + "\n")
        self.output_text.see(tk.END)
        self.root.update()

    def execute_command(self, event=None):
        command_str = self.entry.get().strip()
        if command_str == "" and event is not None:
            return ""
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
        self.update_cwd_label()
        self.entry.delete(0, tk.END)

    def run_startup_script(self):
        sp = self.config.startup_script
        if not sp:
            return
        try:
            with open(sp, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception as e:
            self.writeln(f"failed to open startup script '{sp}': {e}")
            return
        self.writeln(f"--- Running startup script: {sp} ---")
        for raw_line in lines:
            line = raw_line.rstrip("\n")
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
            self.update_cwd_label()
            if tokens and tokens[0] == "exit":
                self.writeln("--- Script requested exit ---")
                return
        self.writeln(f"--- Startup script {sp} finished successfully ---")

    def dump_config_on_start(self):
        self.writeln("=== Emulator configuration (debug dump) ===")
        for k, v in self.config.items():
            self.writeln(f"{k} = {v}")
        self.writeln("==========================================")
        self.update_cwd_label()

    def start(self, run_script_before_mainloop: bool = True):
        self.dump_config_on_start()
        if run_script_before_mainloop:
            self.run_startup_script()
        self.root.mainloop()


SAMPLE_SCRIPTS = {
    "test_vfs_stage4.vfs": """# Тестирование новых команд (Этап 4)
vfs-info
ls /
head /config/info.txt
head -n 2 /config/info.txt
tac /config/info.txt
uniq /data/sample.txt
# Ошибки
tac /notfound.txt
head -n abc /config/info.txt
uniq /not/a/file
exit
"""
}

VFS_CSVS = {
    "vfs_stage4.csv": (
        "Type,Path,Content\n"
        "dir,/config,\n"
        "file,/config/info.txt,SGVsbG8gV29ybGQKVGhpcyBpcyBhIHRlc3QgZmlsZS4KQmVlIHNtYXJ0IQo=\n"
        "dir,/data,\n"
        "file,/data/sample.txt,SGVsbG8KSGVsbG8KV29ybGQKV29ybGQKSGVsbG8K"
    )
}


def create_sample_scripts(path: str = "."):
    created = []
    for name, content in VFS_CSVS.items():
        fp = os.path.join(path, name)
        with open(fp, "w", encoding="utf-8") as f:
            f.write(content)
        created.append(fp)
    for name, content in SAMPLE_SCRIPTS.items():
        fp = os.path.join(path, name)
        with open(fp, "w", encoding="utf-8") as f:
            f.write(content)
        created.append(fp)
    return created


def main():
    parser = argparse.ArgumentParser(description="VFS Shell Emulator (Stage 4)")
    parser.add_argument("--vfs", default="vfs_stage4.csv", help="CSV-файл с VFS")
    parser.add_argument("--startup", default="test_vfs_stage4.vfs", help="Сценарий запуска")
    args = parser.parse_args()

    create_sample_scripts()

    cfg = VFSConfig(vfs_file=args.vfs, startup_script=args.startup)
    vfs, err = load_vfs_from_csv(cfg.vfs_file)
    if err:
        print(err)
        sys.exit(1)
    cfg.vfs = vfs

    app = VFSApp(cfg)
    app.start()


if __name__ == "__main__":
    main()
