import os
import sys
from datetime import datetime, timezone


class VFSConfig:
    def __init__(self, root_path=None, startup_script=None, vfs_file=None):
        self.root_path = root_path or os.getcwd()
        self.startup_script = startup_script
        self.start_time = datetime.now(timezone.utc).isoformat()
        self.vfs_file = vfs_file
        self.vfs = None
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