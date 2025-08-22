import multiprocessing.pool as mpp
import tkinter as tk
import os
from iris.main_analyser import main_analyser

if __name__ == '__main__':
    root = tk.Tk()
    root.title('Main Analyser')

    processor = mpp.Pool()
    app = main_analyser(root,processor)
    app.pack(fill='both',expand=True)

    app.init_extensions(root)

    root.mainloop()

    os._exit(0)