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

class MastersFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.selected_party_id = None
        self.grid_columnconfigure(0, weight=3); self.grid_columnconfigure(1, weight=2); self.grid_rowconfigure(0, weight=1)
        
        # List Card
        c1 = ctk.CTkFrame(self, fg_color=("gray90", "gray13"), corner_radius=10); c1.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(c1, text="REGISTERED PARTIES", font=ctk.CTkFont(size=18, weight="bold")).pack(padx=20, pady=20, anchor="w")
        self.party_list = ttk.Treeview(c1, columns=("ID", "Name", "Mobile"), show="headings")
        self.party_list.heading("ID", text="ID"); self.party_list.column("ID", width=50)
        self.party_list.heading("Name", text="PARTY NAME"); self.party_list.column("Name", width=200)
        self.party_list.heading("Mobile", text="MOBILE"); self.party_list.column("Mobile", width=120)
        self.party_list.pack(fill="both", expand=True, padx=15, pady=(0,15)); self.party_list.bind("<<TreeviewSelect>>", self.on_party_select)

        # Edit Card
        c2 = ctk.CTkFrame(self, fg_color=("gray90", "gray13"), corner_radius=10); c2.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        c2.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(c2, text="MANAGE DETAILS", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, columnspan=2, padx=20, pady=20, sticky="w")
        labels = ["PARTY NAME:", "GST NO:", "MOBILE NO:", "ADDRESS:"]
        self.entries = {}
        for i, txt in enumerate(labels):
            ctk.CTkLabel(c2, text=txt, font=("Arial",12,"bold")).grid(row=i+1, column=0, padx=(20,10), pady=12, sticky="w")
            e = UpperCaseEntry(c2, height=35); e.grid(row=i+1, column=1, padx=(0,20), pady=12, sticky="ew")
            self.entries[txt.replace(':','').replace(' ','_').lower()] = e

        bf = ctk.CTkFrame(c2, fg_color="transparent"); bf.grid(row=5, column=0, columnspan=2, pady=30, sticky="ew"); bf.grid_columnconfigure((0,1,2,3), weight=1)
        ctk.CTkButton(bf, text="NEW", command=self.clear_selection, height=40).grid(row=0, column=0, padx=5, sticky="ew")
        self.save_btn = ctk.CTkButton(bf, text="SAVE", command=self.save_new_party, fg_color="green", height=40); self.save_btn.grid(row=0, column=1, padx=5, sticky="ew")
        self.update_btn = ctk.CTkButton(bf, text="UPDATE", command=self.update_party, height=40); self.update_btn.grid(row=0, column=2, padx=5, sticky="ew")
        self.delete_btn = ctk.CTkButton(bf, text="DELETE", command=self.delete_party, fg_color="#D32F2F", height=40); self.delete_btn.grid(row=0, column=3, padx=5, sticky="ew")
        self.refresh_party_list()

    def refresh_party_list(self):
        for i in self.party_list.get_children(): self.party_list.delete(i)
        for p in database.get_all_parties(): self.party_list.insert("", "end", values=(p[0], p[1], p[3]))
        self.clear_selection()
    def on_party_select(self, e):
        sel = self.party_list.selection()
        if not sel: return
        pid = self.party_list.item(sel[0])['values'][0]
        self.selected_party_id = pid
        p = database.get_party_details(pid)
        vals = [p[1], p[2], p[3], p[4]]
        for i, e in enumerate(self.entries.values()): e.delete(0, 'end'); e.insert(0, vals[i] or "")
        self.save_btn.configure(state="disabled"); self.update_btn.configure(state="normal"); self.delete_btn.configure(state="normal")
    def clear_selection(self):
        self.selected_party_id = None
        if self.party_list.selection(): self.party_list.selection_remove(self.party_list.selection())
        for e in self.entries.values(): e.delete(0, 'end')
        self.save_btn.configure(state="normal"); self.update_btn.configure(state="disabled"); self.delete_btn.configure(state="disabled")
    def save_new_party(self):
        d = {k: e.get().upper() for k, e in self.entries.items()}
        if not d['party_name']: return messagebox.showerror("Error", "NAME REQUIRED")
        if database.add_party(d['party_name'], d['gst_no'], d['mobile_no'], d['address']): messagebox.showinfo("Success", "SAVED"); self.refresh_party_list()
        else: messagebox.showerror("Error", "EXISTS")
    def update_party(self):
        if not self.selected_party_id: return
        d = {k: e.get().upper() for k, e in self.entries.items()}
        if not d['party_name']: return messagebox.showerror("Error", "NAME REQUIRED")
        if database.update_party(self.selected_party_id, d['party_name'], d['gst_no'], d['mobile_no'], d['address']): messagebox.showinfo("Success", "UPDATED"); self.refresh_party_list()
        else: messagebox.showerror("Error", "FAILED")
    def delete_party(self):
        if self.selected_party_id and messagebox.askyesno("Confirm", "DELETE?"):
            if database.delete_party(self.selected_party_id): messagebox.showinfo("Success", "DELETED"); self.refresh_party_list()
            else: messagebox.showerror("Error", "FAILED")