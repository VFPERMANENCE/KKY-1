import argparse
import sys
import os
from config import VFSConfig
from vfs_core import load_vfs_from_csv
from gui import VFSApp
from samples import create_sample_scripts


def main():
    parser = argparse.ArgumentParser(description="VFS Shell Emulator")
    parser.add_argument("--root", default=os.getcwd(), help="Root path for VFS")
    parser.add_argument("--vfs", default="vfs_stage5.csv", help="CSV file with VFS")
    parser.add_argument("--startup", default="test_vfs_stage5.vfs", help="Startup script")
    args = parser.parse_args()

    create_sample_scripts()

    cfg = VFSConfig(root_path=args.root, vfs_file=args.vfs, startup_script=args.startup)
    
    if args.vfs:
        vfs, err = load_vfs_from_csv(cfg.vfs_file)
        if err:
            print(f"Error loading VFS: {err}")
            sys.exit(1)
        cfg.vfs = vfs

    app = VFSApp(cfg)
    app.start()


if __name__ == "__main__":
    main()