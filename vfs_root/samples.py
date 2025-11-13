VFS_CSVS = {
    "vfs_stage1.csv": (
        "Type,Path,Content\n"
        "dir/,,\n"
    ),
    "vfs_stage3.csv": (
        "Type,Path,Content\n"
        "dir/,,\n"
        "dir,/home,,\n"
        "dir,/home/user,,\n"
        "file,/home/user/test.txt,VGVzdCBmaWxlIGNvbnRlbnQ=\n"
        "dir,/var,,\n"
        "dir,/var/log,,\n"
        "file,/var/log/app.log,bG9nIGZpbGUgY29udGVudA==\n"
    ),
    "vfs_stage4.csv": (
        "Type,Path,Content\n"
        "dir/,,\n"
        "dir,/bin,,\n"
        "dir,/etc,,\n"
        "file,/etc/passwd,cm9vdDp4OjA6MDpyb290Oi9yb290Oi9iaW4vYmFzaApiaW46eDoxOjE6YmluOi9iaW46L3NiaW4vbm9sb2dpbg==\n"
        "dir,/tmp,,\n"
        "file,/tmp/data.txt,aGVhZCBjb21tYW5kIHRlc3QKdGFjIGNvbW1hbmQgdGVzdAp1bmlxIGNvbW1hbmQgdGVzdAp0ZXN0IGR1cGxpY2F0ZQp0ZXN0IGR1cGxpY2F0ZQ==\n"
    ),
    "vfs_stage5.csv": (
        "Type,Path,Content\n"
        "dir/,,\n"
        "dir,/config,,\n"
        "file,/config/info.txt,SGVsbG8sIFZGUyE=\n"
        "dir,/data,,\n"
        "dir,/data/docs,,\n"
        "dir,/empty,,\n"
    )
}

STARTUP_SCRIPTS = {
    "test_vfs_stage1.vfs": """# Stage 1 Test Script
conf-dump
ls
cd /nonexistent
exit
""",
    "test_vfs_stage3.vfs": """# Stage 3 Test Script
conf-dump
vfs-info
ls /
ls /home
ls /home/user
cd /home/user
ls
cd /var/log
ls
cd /nonexistent
exit
""",
    "test_vfs_stage4.vfs": """# Stage 4 Test Script
vfs-info
ls /
head /etc/passwd
head -n 2 /etc/passwd
tac /tmp/data.txt
uniq /tmp/data.txt
cd /tmp
ls
exit
""",
    "test_vfs_stage5.vfs": """# Stage 5 Test Script
vfs-info
ls /
mv /config/info.txt /data/
ls /data
mv /data/info.txt /data/config_info.txt
ls /data
mv /notfound /tmp
mv /data/config_info.txt /data/config_info.txt
rmdir /empty
rmdir /data
rmdir /data/docs
exit
"""
}


def create_sample_scripts():
    for name, content in VFS_CSVS.items():
        with open(name, "w", encoding="utf-8") as f:
            f.write(content)
    for name, content in STARTUP_SCRIPTS.items():
        with open(name, "w", encoding="utf-8") as f:
            f.write(content)