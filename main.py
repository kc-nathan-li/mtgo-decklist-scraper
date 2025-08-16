import mtgoScraper as ms
import tkinter as tk
from tkinter import ttk
from tkcalendar import DateEntry
from ttkthemes import ThemedTk
import datetime as dt

# Setup Tkinter
def setupTkinter():
    root = ThemedTk(theme="clearlooks")
    style = ttk.Style()
    style.configure("Custom.TFrame", foreground="black")

    root.columnconfigure(0, minsize=200)
    root.columnconfigure(1, minsize=200)

    # Date Entry Frame
    dateFrm = ttk.Frame(root, padding=10, width=200, style="Custom.TFrame")
    dateFrm.grid(column=0, row=0)
    ttk.Label(dateFrm, text="Start Date:").grid(column=0, row=0)
    startDate = DateEntry(dateFrm, date_pattern="dd/MM/yyyy")
    startDate.set_date(dt.date.today() - dt.timedelta(days=14))
    startDate.grid(column=1,row=0)

    ttk.Label(dateFrm, text="End Date:").grid(column=0, row=1, pady=5)
    endDate = DateEntry(dateFrm, date_pattern="dd/MM/yyyy")
    endDate.grid(column=1,row=1)
    
    # Fromat Selection Frame
    formatFrm = ttk.Frame(root, padding=10, width=400, style="Custom.TFrame")
    formatFrm.grid(column=1, row=0)
    ttk.Label(formatFrm, text="Format: ").grid(column=0, row=0)
    formatOptions = ("Standard", "Pioneer", "Modern", "Legacy")
    formatVar = tk.StringVar()
    formatMenu = ttk.OptionMenu(formatFrm, formatVar, formatOptions[0], *formatOptions)
    formatMenu.grid(row=0, column=1)
    
    root.mainloop()

if __name__ =="__main__":
    setupTkinter()