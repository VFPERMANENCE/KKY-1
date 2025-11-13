import csv
import hashlib
import os
from typing import Tuple, Optional, List


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
        src_node = self.get_node(src)
        if src_node is None:
            return f"mv: cannot stat '{src}': No such file or directory"
        src_parts = [p for p in src.strip('/').split('/') if p]
        src_parent_parts = src_parts[:-1]
        src_name = src_parts[-1]
        src_parent = self.get_node("/" + "/".join(src_parent_parts)) if src_parent_parts else self.root

        dst_node = self.get_node(dst)
        if dst_node and dst_node.type == 'dir':
            if src_name in dst_node.children:
                return f"mv: cannot move '{src}': target already exists in '{dst}'"
            dst_node.children[src_name] = src_node
            del src_parent.children[src_name]
            return f"mv: moved '{src}' -> '{dst}/'"
        else:
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

    def read_file_content(self, path: str) -> Optional[str]:
        node = self.get_node(path)
        if node is None or node.type != 'file':
            return None
        return node.content


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
                return None, "Invalid CSV header format"
            for row in reader:
                if len(row) != 3:
                    return None, f"Invalid number of columns in row: {row}"
                row = [item.lstrip('\ufeff') for item in row]
                vfs_type, vfs_path, vfs_content = [r.strip() for r in row]
                if not vfs_path.startswith('/'):
                    return None, f"Path '{vfs_path}' must start with '/'"
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
                    return None, f"Invalid VFS type: {vfs_type}"
    except Exception as e:
        return None, f"Error loading VFS: {e}"
    vfs.calculate_hash()
    return vfs, None