import tkinter as tk
from tkinter.filedialog import asksaveasfilename, askopenfilename

def main():
    janela = tk.Tk()
    janela.title("Editor de texto")

    janela.rowconfigure(0, minsize=500)
    janela.columnconfigure(1, minsize=600)

    texto = tk.Text(janela, font="Arial 16")
    texto.grid(row = 0, column = 1)

    janela.mainloop()

main()