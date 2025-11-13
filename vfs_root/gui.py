import tkinter as tk
from tkinter import scrolledtext
from config import VFSConfig
from parser import parse_command
from commands import act


class VFSApp:
    def __init__(self, config: VFSConfig):
        self.config = config
        self.root = tk.Tk()
        self.root.title("VFS Shell Emulator")
        self.root.geometry("800x600")
        
        self.cwd_label = tk.Label(self.root, text=f"CWD: {self.config.vfs_cwd}", anchor='w')
        self.cwd_label.pack(padx=10, pady=(10, 0), fill=tk.X)
        
        self.output = scrolledtext.ScrolledText(self.root, wrap=tk.WORD)
        self.output.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        
        self.entry = tk.Entry(self.root)
        self.entry.pack(padx=10, pady=5, fill=tk.X)
        self.entry.bind("<Return>", self.execute_command)
        
        self.btn = tk.Button(self.root, text="Execute", command=self.execute_command)
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
            self.entry.delete(0, tk.END)
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
        if not self.config.startup_script:
            return
            
        try:
            with open(self.config.startup_script, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception as e:
            self.write(f"Error opening script: {e}")
            return
            
        self.write(f"--- Running {self.config.startup_script} ---")
        
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
        self.write("=== VFS Shell Emulator ===")
        if self.config.vfs:
            self.write(f"Loaded VFS: {self.config.vfs.name}")
        self.run_script()
        self.root.mainloop()