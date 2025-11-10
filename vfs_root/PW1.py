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

    def remove_dir(self, path: str) -> str:
        """Удаляет пустую директорию из VFS"""
        if path == "/" or path.strip() == "":
            return "rmdir: cannot remove root directory."
        parts = [p for p in path.strip('/').split('/') if p]
        parent_parts = parts[:-1]
        target_name = parts[-1]
        parent_node = self.get_node("/" + "/".join(parent_parts)) if parent_parts else self.root
        if parent_node is None:
            return f"rmdir: {path}: No such directory"
        if target_name not in parent_node.children:
            return f"rmdir: {path}: No such directory"
        target_node = parent_node.children[target_name]
        if target_node.type != 'dir':
            return f"rmdir: {path}: Not a directory"
        if target_node.children:
            return f"rmdir: {path}: Directory not empty"
        del parent_node.children[target_name]
        return f"rmdir: removed directory '{path}'"

    def move_node(self, src: str, dst: str) -> str:
        """Перемещает или переименовывает узел"""
        src_node = self.get_node(src)
        if src_node is None:
            return f"mv: cannot stat '{src}': No such file or directory"
        src_parts = [p for p in src.strip('/').split('/') if p]
        src_parent_parts = src_parts[:-1]
        src_name = src_parts[-1]
        src_parent = self.get_node("/" + "/".join(src_parent_parts)) if src_parent_parts else self.root

        # Проверим, существует ли цель
        dst_node = self.get_node(dst)
        if dst_node and dst_node.type == 'dir':
            # Перемещаем внутрь директории
            if src_name in dst_node.children:
                return f"mv: cannot move '{src}': target already exists in '{dst}'"
            dst_node.children[src_name] = src_node
            del src_parent.children[src_name]
            return f"mv: moved '{src}' -> '{dst}/'"
        else:
            # Возможно, это новое имя или новый путь
            dst_parts = [p for p in dst.strip('/').split('/') if p]
            dst_parent_parts = dst_parts[:-1]
            dst_name = dst_parts[-1] if dst_parts else src_name
            dst_parent = self.get_node("/" + "/".join(dst_parent_parts)) if dst_parent_parts else self.root
            if dst_parent is None:
                return f"mv: cannot move '{src}' -> '{dst}': No such directory"
            if dst_name in dst_parent.children:
                return f"mv: cannot move '{src}' -> '{dst}': Target already exists"
            dst_parent.children[dst_name] = src_node
            del src_parent.children[src_name]
            src_node.name = dst_name
            return f"mv: renamed/moved '{src}' -> '{dst}'"


def load_vfs_from_csv(file_path: str) -> Tuple[Optional[VFS], Optional[str]]:
    vfs_name = os.path.basename(file_path)
    vfs = VFS(name=vfs_name)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            vfs.raw_data_string = content
            reader = csv.reader(content.splitlines(), delimiter=',')
            header = next(reader)
            if header != ['Type', 'Path', 'Content']:
                return None, "Неверный формат заголовка CSV"
            for row in reader:
                if len(row) != 3:
                    return None, f"Неверное количество столбцов в строке: {row}"
                row = [item.lstrip('\ufeff') for item in row]
                vfs_type, vfs_path, vfs_content = [r.strip() for r in row]
                if not vfs_path.startswith('/'):
                    return None, f"Путь '{vfs_path}' должен начинаться с '/'"
                parts = [p for p in vfs_path.split('/') if p]
                filename = parts[-1] if parts else '/'
                parent_parts = parts[:-1]
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
                    current_node.children[filename] = VFSNode(filename, 'file', vfs_content)
                else:
                    return None, f"Неверный тип VFS: {vfs_type}"
    except Exception as e:
        return None, f"Ошибка загрузки VFS: {e}"
    vfs.calculate_hash()
    return vfs, None


class VFSConfig:
    def __init__(self, root_path=None, startup_script=None, vfs_file=None):
        self.root_path = root_path or os.getcwd()
        self.startup_script = startup_script
        self.start_time = datetime.now(timezone.utc).isoformat()
        self.vfs_file = vfs_file
        self.vfs: Optional[VFS] = None
        self.vfs_cwd = "/"

    def items(self):
        vfs_info = self.vfs.name if self.vfs else "None"
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
        return f"VFS не загружена.", True

    # Базовые команды
    if cmd == "exit":
        return "exit", False
    elif cmd == "vfs-info":
        return f"VFS Name: {config.vfs.name}\nHash: {config.vfs.hash_value}\nCWD: {config.vfs_cwd}", False
    elif cmd == "ls":
        target = config.vfs.get_node(config.vfs_cwd)
        if target.type != 'dir':
            return "not a directory", True
        out = []
        for name, node in target.children.items():
            out.append(f"[{'DIR' if node.type == 'dir' else 'FILE'}] {name}")
        return "\n".join(sorted(out)) if out else "empty", False
    elif cmd == "cd":
        if not args:
            config.vfs_cwd = "/"
            return "", False
        new = os.path.normpath(os.path.join(config.vfs_cwd, args[0])).replace(os.sep, '/')
        node = config.vfs.get_node(new)
        if node is None or node.type != 'dir':
            return f"cd: {args[0]}: not a directory", True
        config.vfs_cwd = new
        return "", False

    elif cmd == "rmdir":
        if not args:
            return "rmdir: missing operand", True
        path = args[0]
        if not path.startswith('/'):
            path = os.path.join(config.vfs_cwd, path).replace(os.sep, '/')
        msg = config.vfs.remove_dir(path)
        return msg, ("error" in msg.lower() or "cannot" in msg.lower())
    elif cmd == "mv":
        if len(args) < 2:
            return "mv: missing file operand", True
        src, dst = args
        if not src.startswith('/'):
            src = os.path.join(config.vfs_cwd, src).replace(os.sep, '/')
        if not dst.startswith('/'):
            dst = os.path.join(config.vfs_cwd, dst).replace(os.sep, '/')
        msg = config.vfs.move_node(src, dst)
        return msg, ("cannot" in msg.lower() or "error" in msg.lower())

    elif cmd == "conf-dump":
        lines = [f"{k}={v}" for k, v in config.items()]
        return "\n".join(lines), False

    else:
        return f"{cmd}: command not found", True

class VFSApp:
    def __init__(self, config: VFSConfig):
        self.config = config
        self.root = tk.Tk()
        self.root.title("VFS Shell (Stage 5)")
        self.root.geometry("800x600")
        self.cwd_label = tk.Label(self.root, text=f"CWD: {self.config.vfs_cwd}", anchor='w')
        self.cwd_label.pack(padx=10, pady=(10, 0), fill=tk.X)
        self.output = scrolledtext.ScrolledText(self.root, wrap=tk.WORD)
        self.output.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        self.entry = tk.Entry(self.root)
        self.entry.pack(padx=10, pady=5, fill=tk.X)
        self.entry.bind("<Return>", self.execute_command)
        self.btn = tk.Button(self.root, text="Отправить", command=self.execute_command)
        self.btn.pack(pady=5)
        self._should_exit = False

    def write(self, text):
        self.output.insert(tk.END, text + "\n")
        self.output.see(tk.END)
        self.root.update()

    def execute_command(self, event=None):
        cmdline = self.entry.get().strip()
        if cmdline == "":
            return
        self.write(f"vfs:{self.config.vfs_cwd}$ {cmdline}")
        tokens, err = parse_command(cmdline)
        if err:
            self.write(err)
            return
        out, is_err = act(tokens, self.config)
        if out == "exit" and not is_err:
            self.write("Bye!")
            self.root.quit()
            return
        self.write(out)
        self.entry.delete(0, tk.END)
        self.cwd_label.config(text=f"CWD: {self.config.vfs_cwd}")

    def run_script(self):
        sp = self.config.startup_script
        if not sp:
            return
        try:
            with open(sp, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception as e:
            self.write(f"Ошибка открытия сценария: {e}")
            return
        self.write(f"--- Running {sp} ---")
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            self.write(f"vfs:{self.config.vfs_cwd}$ {line}")
            tokens, err = parse_command(line)
            if err:
                self.write(err)
                break
            out, is_err = act(tokens, self.config)
            self.write(out)
            if is_err:
                self.write(f"--- Script stopped on: {line} ---")
                break
            if out == "exit":
                break

    def start(self):
        self.write("=== Stage 5 Emulator ===")
        self.run_script()
        self.root.mainloop()


SAMPLE_SCRIPTS = {
    "test_vfs_stage5.vfs": """# Тестирование Этапа 5
vfs-info
ls /
# Попробуем mv
mv /config/info.txt /data/
ls /data
mv /data/info.txt /data/config_info.txt
ls /data
# Ошибки mv
mv /notfound /tmp
mv /data/config_info.txt /data/config_info.txt
# rmdir
rmdir /empty
rmdir /data
rmdir /data/docs
exit
"""
}

VFS_CSVS = {
    "vfs_stage5.csv": (
        "Type,Path,Content\n"
        "dir,/config,\n"
        "file,/config/info.txt,SGVsbG8sIFZGUyE=\n"
        "dir,/data,\n"
        "dir,/data/docs,\n"
        "dir,/empty,\n"
    )
}


def create_sample_scripts():
    for name, content in VFS_CSVS.items():
        with open(name, "w", encoding="utf-8") as f:
            f.write(content)
    for name, content in SAMPLE_SCRIPTS.items():
        with open(name, "w", encoding="utf-8") as f:
            f.write(content)


def main():
    parser = argparse.ArgumentParser(description="VFS Shell Emulator (Stage 5)")
    parser.add_argument("--vfs", default="vfs_stage5.csv", help="CSV-файл с VFS")
    parser.add_argument("--startup", default="test_vfs_stage5.vfs", help="Сценарий запуска")
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
