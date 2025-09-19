import tkinter as tk
from tkinter import scrolledtext
import shlex

def act(a):
    b= shlex.split(a)
    if a== "exit":
        exit()
    if len(b)==0:
        return ""
    if b[0]=="ls":
        return b
    elif b[0]=="cd":
        return b
    else:
        return f'{b[0]}:command not found'
if __name__ =="_main_":
    while True:
        a=input("vfs@ ")
        print (act(a))

def execute_command(e=None):
    command_str = entry.get()
    output = act(command_str)
    output_text.insert(tk.END, f"vfs$ {command_str}\n")
    output_text.insert(tk.END, f"{output}\n")
    entry.delete(0, tk.END)
    output_text.see(tk.END)

root = tk.Tk()
root.title("VFS Shell")
root.geometry("800x600")

output_text = scrolledtext.ScrolledText(root, wrap=tk.WORD, height=20, width=70)
output_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
output_text.config(state=tk.NORMAL)

entry = tk.Entry(root, width=70)
entry.pack(padx=10, pady=5, fill=tk.X)
entry.bind("<Return>", execute_command)

send_button = tk.Button(root, text="Отправить", command=execute_command)
send_button.pack(pady=5)

entry.focus()

root.mainloop()