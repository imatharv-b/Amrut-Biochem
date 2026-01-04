import customtkinter as ctk
import database
import pandas as pd

class PartyDashboardFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.setup_ui()

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(1, weight=1)
        self.header_f = ctk.CTkFrame(self, fg_color="transparent"); self.header_f.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        self.title = ctk.CTkLabel(self.header_f, text="SELECT PARTY FROM REPORTS", font=("Arial", 22, "bold")); self.title.pack(anchor="w")
        self.kpi_f = ctk.CTkFrame(self.header_f, fg_color="transparent"); self.kpi_f.pack(fill="x", pady=10)
        self.hist_f = ctk.CTkScrollableFrame(self, label_text="BILL HISTORY"); self.hist_f.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

    def load_party_data(self, pid):
        p = database.get_party_details(pid)
        k = database.get_party_kpis(pid)
        bills = database.get_all_bills_for_party(pid)

        self.title.configure(text=f"{p[1]} (GST: {p[2] or 'N/A'})")
        for w in self.kpi_f.winfo_children(): w.destroy()
        
        self.add_kpi_card("TOTAL BILLS", k['total_bills'])
        self.add_kpi_card("TOTAL BUSINESS", f"Rs. {k['total_business']:,.2f}")
        self.add_kpi_card("LAST BILL", k['last_bill_date'])

        for w in self.hist_f.winfo_children(): w.destroy()
        for b in bills:
            ctk.CTkButton(self.hist_f, text=f"BILL #{b[0]} | {b[1]} | Rs. {b[2]:,.2f}", anchor="w", fg_color="gray20").pack(fill="x", pady=2)

    def add_kpi_card(self, title, val):
        f = ctk.CTkFrame(self.kpi_f)
        f.pack(side="left", padx=10, expand=True, fill="x")
        ctk.CTkLabel(f, text=title, font=("Arial",10)).pack(pady=(5,0))
        ctk.CTkLabel(f, text=str(val), font=("Arial",16,"bold")).pack(pady=(0,5))