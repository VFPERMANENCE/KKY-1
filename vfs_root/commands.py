import os
import base64
from typing import Tuple, List
from config import VFSConfig


def tac(tokens: List[str], config: VFSConfig) -> Tuple[str, bool]:
    if len(tokens) < 2:
        return "tac: missing file operand", True
    
    path = tokens[1]
    if not path.startswith('/'):
        path = os.path.join(config.vfs_cwd, path).replace(os.sep, '/')
    
    content = config.vfs.read_file_content(path)
    if content is None:
        return f"tac: {tokens[1]}: No such file", True
    
    try:
        decoded_content = base64.b64decode(content).decode('utf-8')
        lines = decoded_content.split('\n')
        reversed_lines = [line for line in reversed(lines) if line.strip()]
        return '\n'.join(reversed_lines), False
    except Exception:
        return "tac: error decoding file content", True


def head(tokens: List[str], config: VFSConfig) -> Tuple[str, bool]:
    if len(tokens) < 2:
        return "head: missing file operand", True
    
    lines_count = 10
    file_index = 1
    
    if len(tokens) >= 3 and tokens[1] == '-n':
        try:
            lines_count = int(tokens[2])
            file_index = 3
        except ValueError:
            return "head: invalid number of lines", True
    
    if len(tokens) <= file_index:
        return "head: missing file operand", True
    
    path = tokens[file_index]
    if not path.startswith('/'):
        path = os.path.join(config.vfs_cwd, path).replace(os.sep, '/')
    
    content = config.vfs.read_file_content(path)
    if content is None:
        return f"head: {tokens[file_index]}: No such file", True
    
    try:
        decoded_content = base64.b64decode(content).decode('utf-8')
        lines = decoded_content.split('\n')[:lines_count]
        return '\n'.join(lines), False
    except Exception:
        return "head: error decoding file content", True


def uniq(tokens: List[str], config: VFSConfig) -> Tuple[str, bool]:
    if len(tokens) < 2:
        return "uniq: missing file operand", True
    
    path = tokens[1]
    if not path.startswith('/'):
        path = os.path.join(config.vfs_cwd, path).replace(os.sep, '/')
    
    content = config.vfs.read_file_content(path)
    if content is None:
        return f"uniq: {tokens[1]}: No such file", True
    
    try:
        decoded_content = base64.b64decode(content).decode('utf-8')
        lines = decoded_content.split('\n')
        seen = set()
        unique_lines = []
        for line in lines:
            if line not in seen:
                seen.add(line)
                unique_lines.append(line)
        return '\n'.join(unique_lines), False
    except Exception:
        return "uniq: error decoding file content", True


def act(tokens: List[str], config: VFSConfig) -> Tuple[str, bool]:
    if tokens is None:
        return "parse error", True
    if len(tokens) == 0:
        return "", False
        
    cmd = tokens[0]
    args = tokens[1:]
    
    if not config.vfs and cmd not in ("exit", "conf-dump"):
        return "VFS not loaded.", True

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
    elif cmd == "tac":
        return tac(tokens, config)
    elif cmd == "head":
        return head(tokens, config)
    elif cmd == "uniq":
        return uniq(tokens, config)
    elif cmd == "conf-dump":
        lines = [f"{k}={v}" for k, v in config.items()]
        return "\n".join(lines), False
    else:
        return f"{cmd}: command not found", True