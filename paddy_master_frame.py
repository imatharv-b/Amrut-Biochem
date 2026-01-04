import customtkinter as ctk
from tkinter import messagebox, ttk
import database

# --- Auto-Caps Entry ---
class UpperCaseEntry(ctk.CTkEntry):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.bind("<KeyRelease>", self.force_caps)
    def force_caps(self, event):
        if event.keysym in ("BackSpace", "Delete", "Left", "Right", "Up", "Down", "Tab", "Shift_L", "Shift_R", "Caps_Lock", "Control_L", "Control_R"): return
        try:
            current_pos = self.index(ctk.INSERT); val = self.get()
            if val != val.upper(): self.delete(0, "end"); self.insert(0, val.upper()); self.icursor(current_pos)
        except: pass

class PaddyMasterFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.selected_variety_id = None
        self.grid_columnconfigure(0, weight=3); self.grid_columnconfigure(1, weight=2); self.grid_rowconfigure(0, weight=1)

        # List Card
        c1 = ctk.CTkFrame(self, fg_color=("gray90", "gray13"), corner_radius=10); c1.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(c1, text="PADDY VARIETIES", font=ctk.CTkFont(size=18, weight="bold")).pack(padx=20, pady=20, anchor="w")
        self.variety_list = ttk.Treeview(c1, columns=("ID", "Name", "Rate"), show="headings")
        self.variety_list.heading("ID", text="ID"); self.variety_list.column("ID", width=0, stretch=False)
        self.variety_list.heading("Name", text="VARIETY NAME"); self.variety_list.column("Name", width=200)
        self.variety_list.heading("Rate", text="BROKERAGE/QTL"); self.variety_list.column("Rate", width=120)
        self.variety_list.pack(fill="both", expand=True, padx=15, pady=(0,15)); self.variety_list.bind("<<TreeviewSelect>>", self.on_select)

        # Edit Card
        c2 = ctk.CTkFrame(self, fg_color=("gray90", "gray13"), corner_radius=10); c2.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        c2.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(c2, text="MANAGE VARIETY", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, columnspan=2, padx=20, pady=20, sticky="w")
        
        ctk.CTkLabel(c2, text="VARIETY NAME:", font=("Arial",12,"bold")).grid(row=1, column=0, padx=(20,10), pady=15, sticky="w")
        self.variety_name_entry = UpperCaseEntry(c2, height=35); self.variety_name_entry.grid(row=1, column=1, padx=(0,20), pady=15, sticky="ew")
        
        ctk.CTkLabel(c2, text="BROKERAGE RATE/QTL:", font=("Arial",12,"bold")).grid(row=2, column=0, padx=(20,10), pady=15, sticky="w")
        self.brokerage_rate_entry = ctk.CTkEntry(c2, height=35); self.brokerage_rate_entry.grid(row=2, column=1, padx=(0,20), pady=15, sticky="ew")

        bf = ctk.CTkFrame(c2, fg_color="transparent"); bf.grid(row=3, column=0, columnspan=2, pady=30, sticky="ew"); bf.grid_columnconfigure((0,1,2), weight=1)
        ctk.CTkButton(bf, text="NEW", command=self.clear_selection, height=40).grid(row=0, column=0, padx=5, sticky="ew")
        self.save_button = ctk.CTkButton(bf, text="SAVE", command=self.save_new_variety, fg_color="green", height=40); self.save_button.grid(row=0, column=1, padx=5, sticky="ew")
        self.update_button = ctk.CTkButton(bf, text="UPDATE", command=self.update_variety, height=40); self.update_button.grid(row=0, column=2, padx=5, sticky="ew")
        self.refresh_variety_list()

    def refresh_variety_list(self):
        for i in self.variety_list.get_children(): self.variety_list.delete(i)
        for v in database.get_all_paddy_varieties(): self.variety_list.insert("", "end", values=v)
        self.clear_selection()
    def on_select(self, e):
        sel = self.variety_list.selection()
        if not sel: return
        vals = self.variety_list.item(sel[0])['values']
        self.selected_variety_id = vals[0]
        self.variety_name_entry.delete(0, 'end'); self.variety_name_entry.insert(0, vals[1])
        self.brokerage_rate_entry.delete(0, 'end'); self.brokerage_rate_entry.insert(0, str(vals[2]))
        self.save_button.configure(state="disabled"); self.update_button.configure(state="normal")
    def clear_selection(self):
        self.selected_variety_id = None
        if self.variety_list.selection(): self.variety_list.selection_remove(self.variety_list.selection())
        self.variety_name_entry.delete(0, 'end'); self.brokerage_rate_entry.delete(0, 'end')
        self.save_button.configure(state="normal"); self.update_button.configure(state="disabled")
    def save_new_variety(self):
        n = self.variety_name_entry.get().upper(); r = self.brokerage_rate_entry.get()
        if not n or not r: return messagebox.showerror("Error", "REQUIRED FIELDS")
        try: 
            if database.add_paddy_variety(n, float(r)): messagebox.showinfo("Success", "SAVED"); self.refresh_variety_list()
            else: messagebox.showerror("Error", "EXISTS")
        except: messagebox.showerror("Error", "INVALID RATE")
    def update_variety(self):
        if not self.selected_variety_id: return
        n = self.variety_name_entry.get().upper(); r = self.brokerage_rate_entry.get()
        if not n or not r: return messagebox.showerror("Error", "REQUIRED FIELDS")
        try:
            if database.update_paddy_variety(self.selected_variety_id, n, float(r)): messagebox.showinfo("Success", "UPDATED"); self.refresh_variety_list()
            else: messagebox.showerror("Error", "FAILED")
        except: messagebox.showerror("Error", "INVALID RATE")