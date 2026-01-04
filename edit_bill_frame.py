import customtkinter as ctk
from tkinter import messagebox, Toplevel, simpledialog
from tkcalendar import Calendar
from datetime import datetime
import database
import pdf_generator

# --- Custom Widgets (Same as BillingFrame) ---
class UpperCaseEntry(ctk.CTkEntry):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.bind("<KeyRelease>", self.force_caps)
        self.bind("<FocusIn>", self.select_all)

    def force_caps(self, event):
        if event.keysym in ("BackSpace", "Delete", "Left", "Right", "Up", "Down", "Tab", "Shift_L", "Shift_R", "Caps_Lock", "Control_L", "Control_R"): return
        try:
            current_pos = self.index(ctk.INSERT); val = self.get()
            if val != val.upper(): self.delete(0, "end"); self.insert(0, val.upper()); self.icursor(current_pos)
        except: pass

    def select_all(self, event):
        self.after(50, lambda: self.select_range(0, 'end'))

class AutocompleteEntry(UpperCaseEntry): 
    def __init__(self, master, values=None, **kwargs):
        super().__init__(master, **kwargs)
        self.values = values if values else []; self.bind("<KeyRelease>", self.on_key_release); self.bind("<FocusOut>", lambda e: self.after(200, self.hide_suggestions)); self.bind("<Next>", self.select_top_match); self._suggestion_list = None
    def on_key_release(self, event):
        self.force_caps(event)
        if event.keysym in ("Up", "Down", "Return", "Escape", "Tab", "Next", "Shift_L", "Shift_R", "Caps_Lock"): return
        typed = self.get().lower(); 
        if not typed: self.hide_suggestions(); return
        matches = [v for v in self.values if typed in v.lower()]; self.show_suggestions(matches)
    def show_suggestions(self, matches):
        self.hide_suggestions(); 
        if not matches: return
        self._suggestion_list = Toplevel(self, bg="#2b2b2b"); self._suggestion_list.wm_overrideredirect(True); self._suggestion_list.wm_geometry(f"+{self.winfo_rootx()}+{self.winfo_rooty() + self.winfo_height()}")
        scroll = ctk.CTkScrollableFrame(self._suggestion_list); scroll.pack(fill="both", expand=True)
        for m in matches: ctk.CTkButton(scroll, text=m.upper(), anchor="w", fg_color="transparent", hover_color="gray30", command=lambda v=m: self.select(v)).pack(fill="x")
    def select_top_match(self, event):
        if self._suggestion_list and self.current_matches: self.select(self.current_matches[0]); return "break"
    def hide_suggestions(self):
        if self._suggestion_list: self._suggestion_list.destroy(); self._suggestion_list = None
    def select(self, value):
        self.delete(0, 'end'); self.insert(0, value.upper()); self.hide_suggestions()
        if hasattr(self.master.master, 'update_totals'): self.master.master.update_totals()
        self.event_generate("<Return>") 

# --- Edit Bill Frame ---
class EditBillFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.item_rows = []; self.editing_bill_no = None
        self.grid_columnconfigure((0, 1, 2), weight=1, uniform="a")
        
        # --- SEARCH BAR ---
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 20))
        ctk.CTkLabel(search_frame, text="ENTER BILL NO TO EDIT:", font=("Arial", 16, "bold")).pack(side="left", padx=20)
        self.search_entry = ctk.CTkEntry(search_frame, width=150, font=("Arial", 16)); self.search_entry.pack(side="left", padx=10)
        
        # SEARCH BUTTON (Triggers Password)
        ctk.CTkButton(search_frame, text="SEARCH & LOAD", command=self.auth_and_search, font=("Arial", 14, "bold"), width=150).pack(side="left", padx=10)

        self.setup_ui()
        self.lock_ui(True) # Start Locked

    def setup_ui(self):
        card_color = ("gray90", "gray13") 
        
        # C1: Bill Details
        c1 = ctk.CTkFrame(self, fg_color=card_color, corner_radius=10); c1.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(c1, text="BILL DETAILS", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(15,10))
        self.bill_no = self.create_field(c1, "BILL NO:", "", readonly=True)
        self.date = self.create_field(c1, "DATE:", ""); self.date.bind("<Button-1>", self.open_cal)
        self.party = self.create_autocomplete(c1, "PARTY NAME:")
        self.lorry = self.create_field(c1, "LORRY NO:")

        # C2: Weights
        c2 = ctk.CTkFrame(self, fg_color=card_color, corner_radius=10); c2.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(c2, text="WEIGHTS (QTL)", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(15,10))
        self.total_bags = self.create_field(c2, "TOTAL BAGS:")
        self.w1 = self.create_field(c2, "WEIGHT 1:", "0")
        self.w2 = self.create_field(c2, "WEIGHT 2:", "0")
        self.w3 = self.create_field(c2, "WEIGHT 3:", "0")
        self.net_weight_lbl = ctk.CTkLabel(c2, text="NET WT: 0.00 QTL", font=("Arial", 20, "bold"), text_color="#33a1c9"); self.net_weight_lbl.pack(pady=20)
        for w in [self.w1, self.w2, self.w3, self.total_bags]: w.bind("<KeyRelease>", self.update_totals)

        # C3: Charges
        c3 = ctk.CTkFrame(self, fg_color=card_color, corner_radius=10); c3.grid(row=1, column=2, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(c3, text="CHARGES", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(15,10))
        self.discount = self.create_field(c3, "DISCOUNT (%):", "0")
        self.hamali = self.create_field(c3, "HAMALI:", "0")
        self.brokerage = self.create_field(c3, "BROKERAGE:", "0")
        self.others_a = self.create_field(c3, "OTHERS AMT:", "0")
        self.others_d = self.create_field(c3, "OTHERS DESC:")
        for w in [self.discount, self.hamali, self.others_a]: w.bind("<KeyRelease>", self.update_totals)

        # Items
        items_container = ctk.CTkFrame(self, fg_color=card_color, corner_radius=10)
        items_container.grid(row=2, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(items_container, text="PADDY ITEMS LIST", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(15,5), anchor="w", padx=20)
        self.items_frame = ctk.CTkScrollableFrame(items_container, fg_color="transparent", height=250); self.items_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent"); btn_frame.grid(row=3, column=0, columnspan=3, sticky="ew", padx=10, pady=10)
        self.add_btn = ctk.CTkButton(btn_frame, text="+ ADD ITEM", command=self.add_item_row, width=150, font=ctk.CTkFont(weight="bold")); self.add_btn.pack(side="left", padx=10)
        self.save_btn = ctk.CTkButton(btn_frame, text="UPDATE BILL", fg_color="orange", hover_color="darkorange", height=50, width=220, font=("Arial", 16, "bold"), command=self.update_bill_db, state="disabled"); self.save_btn.pack(side="right")

    def on_show(self):
        self.party.values = [p[1] for p in database.get_all_parties()]
        self.paddy_data = {v[1]: v[2] for v in database.get_all_paddy_varieties()}
        # Do not clear search entry so user can see what they typed, but clear form
        self.clear_form(clear_search=False)
        self.lock_ui(True)

    def auth_and_search(self):
        bno = self.search_entry.get()
        if not bno: return
        
        # --- PASSWORD PROMPT ---
        # Using standard simpledialog because customtkinter doesn't have a built-in password dialog
        pwd = simpledialog.askstring("Authorized Access", "Enter Admin Password:", show='*')
        
        if pwd == "admin123": # <--- CHANGE PASSWORD HERE
            self.search_bill()
        else:
            messagebox.showerror("Access Denied", "Incorrect Password")

    def search_bill(self):
        bno = self.search_entry.get()
        try: bill_id = int(bno)
        except: messagebox.showerror("Error", "Invalid Bill Number"); return
        
        bill = database.get_bill_details(bill_id)
        if not bill: messagebox.showerror("Error", "Bill Not Found"); return
        
        h = bill['header']; items = bill['items']
        self.editing_bill_no = bill_id
        
        # Unlock UI for editing
        self.lock_ui(False)
        
        # Populate
        self.bill_no.configure(state="normal"); self.bill_no.delete(0, 'end'); self.bill_no.insert(0, str(h['bill_no'])); self.bill_no.configure(state="readonly")
        self.date.delete(0, 'end'); self.date.insert(0, h['bill_date'])
        self.party.delete(0, 'end'); self.party.insert(0, h['party_name'])
        self.lorry.delete(0, 'end'); self.lorry.insert(0, h['lorry_no'] or "")
        
        self.total_bags.delete(0, 'end'); self.total_bags.insert(0, str(h['total_bags']))
        self.w1.delete(0, 'end'); self.w1.insert(0, str(h['truck_weight1_kg']))
        self.w2.delete(0, 'end'); self.w2.insert(0, str(h['truck_weight2_kg']))
        self.w3.delete(0, 'end'); self.w3.insert(0, str(h['truck_weight3_kg']))
        
        self.discount.delete(0, 'end'); self.discount.insert(0, str(h['discount_percent']))
        self.hamali.delete(0, 'end'); self.hamali.insert(0, str(int(h['hamali'])))
        self.brokerage.delete(0, 'end'); self.brokerage.insert(0, str(int(h['brokerage'])))
        self.others_d.delete(0, 'end'); self.others_d.insert(0, h['others_desc'] or "")
        self.others_a.delete(0, 'end'); self.others_a.insert(0, str(int(h['others_amount'])))
        
        # Clear old items UI first
        for r in self.item_rows: r['frame'].destroy()
        self.item_rows = []
        
        for item in items: self.add_item_row(item['paddy_type'], item['bags'], item['moisture'], item['base_rate'])
        self.update_totals()
        self.save_btn.configure(state="normal") 

    def lock_ui(self, lock):
        state = "disabled" if lock else "normal"
        # Disable all entry fields except search
        for child in self.winfo_children():
            if isinstance(child, ctk.CTkEntry) and child != self.search_entry:
                child.configure(state=state)
        # We manually manage the fields because they are inside sub-frames
        for frame in [self.items_frame]: # And other containers
             for widget in frame.winfo_children():
                 try: widget.configure(state=state)
                 except: pass
        self.add_btn.configure(state=state)
        if lock: self.save_btn.configure(state="disabled")

    def update_bill_db(self):
        if not self.editing_bill_no: return
        try:
            s_float = lambda e: float(e.get()) if e.get().strip() else 0.0
            s_int = lambda e: int(e.get()) if e.get().strip() else 0
            header = {"bill_no": s_int(self.bill_no), "party_name": self.party.get().upper(), "date": self.date.get(), "lorry_no": self.lorry.get().upper(), "total_bags": s_int(self.total_bags), "truck_weight1_kg": s_float(self.w1), "truck_weight2_kg": s_float(self.w2), "truck_weight3_kg": s_float(self.w3), "discount_percent": s_float(self.discount), "brokerage": s_float(self.brokerage), "hamali": s_float(self.hamali), "others_desc": self.others_d.get().upper(), "others_amount": s_float(self.others_a)}
            if not header["party_name"]: return messagebox.showerror("Error", "PARTY NAME REQUIRED")
            if header["total_bags"] == 0: return messagebox.showerror("Error", "TOTAL BAGS 0")
            items = []
            for r in self.item_rows: items.append({"paddy_type": r["type"].get().upper(), "bags": s_int(r["bags"]), "moisture": s_float(r["moist"]), "base_rate": s_float(r["rate"])})
            
            res = database.update_bill(self.editing_bill_no, header, items)
            
            if isinstance(res, int):
                if pdf_generator.generate_bill_pdf(database.get_bill_details(res)):
                    messagebox.showinfo("SUCCESS", f"BILL #{res} UPDATED & PDF REGENERATED!")
                else: messagebox.showwarning("WARNING", "UPDATED BUT PDF FAILED")
                self.clear_form()
                self.lock_ui(True) # Lock again after save
            else: messagebox.showerror("DB ERROR", res)
        except Exception as e: messagebox.showerror("ERROR", str(e))

    # Helper methods (Same as before)
    def create_field(self, p, lbl, default="", readonly=False):
        f = ctk.CTkFrame(p, fg_color="transparent"); f.pack(fill="x", pady=5, padx=15)
        ctk.CTkLabel(f, text=lbl, width=120, anchor="w", font=("Arial",12,"bold")).pack(side="left")
        e = UpperCaseEntry(f, height=35); e.insert(0, default); e.pack(side="right", fill="x", expand=True)
        if readonly: e.configure(state="readonly")
        return e
    def create_autocomplete(self, p, lbl):
        f = ctk.CTkFrame(p, fg_color="transparent"); f.pack(fill="x", pady=5, padx=15)
        ctk.CTkLabel(f, text=lbl, width=120, anchor="w", font=("Arial",12,"bold")).pack(side="left")
        e = AutocompleteEntry(f, height=35); e.pack(side="right", fill="x", expand=True)
        return e
    def open_cal(self, e):
        top = Toplevel(self); cal = Calendar(top, date_pattern='y-mm-dd'); cal.pack(pady=10)
        ctk.CTkButton(top, text="SELECT", command=lambda: [self.date.delete(0,'end'), self.date.insert(0, cal.get_date()), top.destroy()]).pack(pady=10)
    def add_item_row(self, t_val="", b_val="", m_val="", r_val=""):
        row = ctk.CTkFrame(self.items_frame, fg_color=("gray95", "gray20")); row.pack(fill="x", pady=4)
        t = AutocompleteEntry(row, values=list(self.paddy_data.keys()) if hasattr(self, 'paddy_data') else [], placeholder_text="TYPE", height=35); t.insert(0, t_val); t.pack(side="left", fill="x", expand=True, padx=5)
        b = UpperCaseEntry(row, width=90, placeholder_text="BAGS", height=35); b.insert(0, str(b_val)); b.pack(side="left", padx=5)
        m = UpperCaseEntry(row, width=90, placeholder_text="MOIST %", height=35); m.insert(0, str(m_val)); m.pack(side="left", padx=5)
        r = UpperCaseEntry(row, width=110, placeholder_text="RATE/QTL", height=35); r.insert(0, str(r_val)); r.pack(side="left", padx=5)
        rd = {"frame": row, "type": t, "bags": b, "moist": m, "rate": r}
        ctk.CTkButton(row, text="X", width=40, height=35, fg_color="#D32F2F", hover_color="#B71C1C", command=lambda: self.remove_row(rd)).pack(side="left", padx=5)
        for w in [t, b, m, r]: w.bind("<KeyRelease>", self.update_totals)
        self.item_rows.append(rd)
    def remove_row(self, rd):
        if len(self.item_rows) > 0: rd["frame"].destroy(); self.item_rows.remove(rd); self.update_totals()
    def update_totals(self, *args):
        try:
            s_float = lambda e: float(e.get()) if e.get().strip() else 0.0
            s_int = lambda e: int(e.get()) if e.get().strip() else 0
            ws = [s_float(self.w1), s_float(self.w2), s_float(self.w3)]
            nw = min([w for w in ws if w > 0]) if any(w > 0 for w in ws) else 0.0
            self.net_weight_lbl.configure(text=f"NET WT: {nw:,.2f} QTL")
            # Logic for auto brokerage / hamali removed here as per edit mode standard, just calc basic totals if needed
        except: pass
    def clear_form(self, clear_search=True):
        if clear_search: self.search_entry.delete(0, 'end'); self.save_btn.configure(state="disabled")
        for e in [self.party, self.lorry, self.total_bags, self.others_d]: e.delete(0, 'end')
        for e in [self.w1, self.w2, self.w3, self.discount, self.hamali, self.others_a, self.brokerage]: e.delete(0, 'end'); e.insert(0, "0")
        for r in self.item_rows: r['frame'].destroy()
        self.item_rows = []
        self.bill_no.configure(state="normal"); self.bill_no.delete(0, 'end'); self.bill_no.configure(state="readonly")
        self.update_totals()