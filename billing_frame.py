import customtkinter as ctk
from tkinter import messagebox, Toplevel
from tkcalendar import Calendar
from datetime import datetime
import os
import database
import pdf_generator

# ======================================================
# CUSTOM WIDGETS (Auto-Caps, Autocomplete, Select-All)
# ======================================================

class UpperCaseEntry(ctk.CTkEntry):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.bind("<KeyRelease>", self.force_caps)
        self.bind("<FocusIn>", self.select_all) # FEATURE: Select All on Tab

    def force_caps(self, event):
        # Ignore navigation keys
        if event.keysym in ("BackSpace", "Delete", "Left", "Right", "Up", "Down", "Tab", "Shift_L", "Shift_R", "Caps_Lock", "Control_L", "Control_R"): 
            return
        try:
            current_pos = self.index(ctk.INSERT)
            val = self.get()
            if val != val.upper():
                self.delete(0, "end")
                self.insert(0, val.upper())
                self.icursor(current_pos)
        except: pass

    def select_all(self, event):
        # Select all text when focusing in (Delayed slightly to work after default binding)
        self.after(50, lambda: self.select_range(0, 'end'))

class AutocompleteEntry(UpperCaseEntry): 
    def __init__(self, master, values=None, **kwargs):
        super().__init__(master, **kwargs)
        self.values = values if values else []
        self.current_matches = [] 
        self.bind("<KeyRelease>", self.on_key_release)
        self.bind("<FocusOut>", lambda e: self.after(200, self.hide_suggestions))
        self.bind("<Next>", self.select_top_match)
        self._suggestion_list = None

    def on_key_release(self, event):
        self.force_caps(event)
        if event.keysym in ("Up", "Down", "Return", "Escape", "Tab", "Next", "Shift_L", "Shift_R", "Caps_Lock"): return
        typed = self.get().lower()
        if not typed: self.hide_suggestions(); return
        matches = [v for v in self.values if typed in v.lower()]
        self.show_suggestions(matches)

    def show_suggestions(self, matches):
        self.current_matches = matches
        self.hide_suggestions()
        if not matches: return
        self._suggestion_list = Toplevel(self, bg="#2b2b2b")
        self._suggestion_list.wm_overrideredirect(True)
        self._suggestion_list.wm_geometry(f"+{self.winfo_rootx()}+{self.winfo_rooty() + self.winfo_height()}")
        scroll = ctk.CTkScrollableFrame(self._suggestion_list)
        scroll.pack(fill="both", expand=True)
        for m in matches:
            ctk.CTkButton(scroll, text=m.upper(), anchor="w", fg_color="transparent", hover_color="gray30", command=lambda v=m: self.select(v)).pack(fill="x")

    def select_top_match(self, event):
        if self._suggestion_list and self.current_matches: self.select(self.current_matches[0]); return "break"

    def hide_suggestions(self):
        if self._suggestion_list: self._suggestion_list.destroy(); self._suggestion_list = None

    def select(self, value):
        self.delete(0, 'end'); self.insert(0, value.upper()); self.hide_suggestions()
        if isinstance(self.master.master, BillingFrame): self.master.master.update_totals()
        self.event_generate("<Return>") 

# ======================================================
# MAIN BILLING SCREEN
# ======================================================

class BillingFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.item_rows = []
        self.grid_columnconfigure((0, 1, 2), weight=1, uniform="a")
        self.setup_ui()

    def setup_ui(self):
        # FEATURE: Heading Title
        ctk.CTkLabel(self, text="PURCHASE ENTRY (INWARD)", font=("Arial", 22, "bold"), text_color="#33a1c9").grid(row=0, column=0, columnspan=3, pady=(0,20))

        card_color = ("gray90", "gray13") 

        # --- Card 1: Bill & Party Info ---
        c1 = ctk.CTkFrame(self, fg_color=card_color, corner_radius=10)
        c1.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(c1, text="BILL DETAILS", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(15,10))
        
        # FEATURE: Read-Only Bill Number
        self.bill_no = self.create_field(c1, "BILL NO:", str(database.get_next_bill_number()))
        self.bill_no.configure(state="readonly") 
        
        self.date = self.create_field(c1, "DATE:", datetime.now().strftime("%Y-%m-%d"))
        self.date.bind("<Button-1>", self.open_cal)
        self.party = self.create_autocomplete(c1, "PARTY NAME:")
        self.lorry = self.create_field(c1, "LORRY NO:")

        # --- Card 2: Weights & Bags ---
        c2 = ctk.CTkFrame(self, fg_color=card_color, corner_radius=10)
        c2.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(c2, text="WEIGHTS (QTL)", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(15,10))
        
        self.total_bags = self.create_field(c2, "TOTAL BAGS:")
        self.w1 = self.create_field(c2, "WEIGHT 1:", "0")
        self.w2 = self.create_field(c2, "WEIGHT 2:", "0")
        self.w3 = self.create_field(c2, "WEIGHT 3:", "0")
        
        self.net_weight_lbl = ctk.CTkLabel(c2, text="NET WT: 0.00 QTL", font=("Arial", 20, "bold"), text_color="#33a1c9")
        self.net_weight_lbl.pack(pady=20)
        
        for w in [self.w1, self.w2, self.w3, self.total_bags]: w.bind("<KeyRelease>", self.update_totals)

        # --- Card 3: Charges ---
        c3 = ctk.CTkFrame(self, fg_color=card_color, corner_radius=10)
        c3.grid(row=1, column=2, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(c3, text="CHARGES", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(15,10))
        
        self.discount = self.create_field(c3, "DISCOUNT (%):", "0")
        self.hamali = self.create_field(c3, "HAMALI:", "0") # FEATURE: Manual Hamali
        self.brokerage = self.create_field(c3, "BROKERAGE:", "0") # FEATURE: Auto-calc
        
        # FEATURE: Swapped Order (Amount first)
        self.others_a = self.create_field(c3, "OTHERS AMT:", "0")
        self.others_d = self.create_field(c3, "OTHERS DESC:")
        
        for w in [self.discount, self.hamali, self.others_a]: w.bind("<KeyRelease>", self.update_totals)

        # --- Items Section ---
        items_container = ctk.CTkFrame(self, fg_color=card_color, corner_radius=10)
        items_container.grid(row=2, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")
        
        # FEATURE: Dynamic Remaining Bags Counter
        header_frame = ctk.CTkFrame(items_container, fg_color="transparent")
        header_frame.pack(fill="x", pady=(15,5), padx=20)
        ctk.CTkLabel(header_frame, text="PADDY ITEMS LIST", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")
        
        self.alloc_lbl = ctk.CTkLabel(header_frame, text="(Remaining: 0)", font=("Arial", 14, "bold"), text_color="gray")
        self.alloc_lbl.pack(side="right")

        self.items_frame = ctk.CTkScrollableFrame(items_container, fg_color="transparent", height=250)
        self.items_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # --- Action Buttons ---
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=3, column=0, columnspan=3, sticky="ew", padx=10, pady=10)
        
        self.add_btn = ctk.CTkButton(btn_frame, text="+ ADD ANOTHER ITEM", command=self.add_item_row, height=40, font=ctk.CTkFont(weight="bold"))
        self.add_btn.pack(side="left")
        
        # FEATURE: Preview Button
        self.preview_btn = ctk.CTkButton(btn_frame, text="PREVIEW BILL", fg_color="#1f6aa5", hover_color="#144d7a", height=50, width=180, font=("Arial", 14, "bold"), command=self.preview_bill)
        self.preview_btn.pack(side="right", padx=(10, 0))

        self.save_btn = ctk.CTkButton(btn_frame, text="SAVE & PRINT BILL", fg_color="green", hover_color="darkgreen", height=50, width=200, font=("Arial", 16, "bold"), command=self.process_bill)
        self.save_btn.pack(side="right")

        self.add_item_row() 

    # --- UI Logic Methods ---
    def on_show(self):
        self.party.values = [p[1] for p in database.get_all_parties()]
        self.paddy_data = {v[1]: v[2] for v in database.get_all_paddy_varieties()}
        for r in self.item_rows: r["type"].values = list(self.paddy_data.keys())
        self.setup_navigation()

    def create_field(self, p, lbl, default=""):
        f = ctk.CTkFrame(p, fg_color="transparent"); f.pack(fill="x", pady=5, padx=15)
        ctk.CTkLabel(f, text=lbl, width=120, anchor="w", font=("Arial",12,"bold")).pack(side="left")
        e = UpperCaseEntry(f, height=35); e.insert(0, default); e.pack(side="right", fill="x", expand=True)
        return e

    def create_autocomplete(self, p, lbl):
        f = ctk.CTkFrame(p, fg_color="transparent"); f.pack(fill="x", pady=5, padx=15)
        ctk.CTkLabel(f, text=lbl, width=120, anchor="w", font=("Arial",12,"bold")).pack(side="left")
        e = AutocompleteEntry(f, height=35); e.pack(side="right", fill="x", expand=True)
        return e

    def open_cal(self, event):
        top = Toplevel(self); cal = Calendar(top, date_pattern='y-mm-dd'); cal.pack(pady=10)
        ctk.CTkButton(top, text="SELECT", command=lambda: [self.date.delete(0,'end'), self.date.insert(0, cal.get_date()), top.destroy()]).pack(pady=10)

    def add_item_row(self):
        row = ctk.CTkFrame(self.items_frame, fg_color=("gray95", "gray20")); row.pack(fill="x", pady=4)
        t = AutocompleteEntry(row, values=list(self.paddy_data.keys()) if hasattr(self, 'paddy_data') else [], placeholder_text="TYPE", height=35)
        t.pack(side="left", fill="x", expand=True, padx=5, pady=5)
        b = UpperCaseEntry(row, width=90, placeholder_text="BAGS", height=35); b.pack(side="left", padx=5, pady=5)
        m = UpperCaseEntry(row, width=90, placeholder_text="MOIST %", height=35); m.pack(side="left", padx=5, pady=5)
        r = UpperCaseEntry(row, width=110, placeholder_text="RATE/QTL", height=35); r.pack(side="left", padx=5, pady=5)
        
        rd = {"frame": row, "type": t, "bags": b, "moist": m, "rate": r}
        
        ctk.CTkButton(row, text="X", width=40, height=35, fg_color="#D32F2F", hover_color="#B71C1C", command=lambda: self.remove_row(rd)).pack(side="left", padx=5, pady=5)
        
        for w in [t, b, m, r]: w.bind("<KeyRelease>", self.update_totals)
        self.item_rows.append(rd); self.setup_navigation()

    def remove_row(self, rd):
        if len(self.item_rows) > 1: rd["frame"].destroy(); self.item_rows.remove(rd); self.update_totals(); self.setup_navigation()

    def update_totals(self, *args):
        try:
            def safe_float(e): return float(e.get()) if e.get().strip() else 0.0
            def safe_int(e): return int(e.get()) if e.get().strip() else 0
            
            # 1. Weights Calculation
            ws = [safe_float(self.w1), safe_float(self.w2), safe_float(self.w3)]
            nw = min([w for w in ws if w > 0]) if any(w > 0 for w in ws) else 0.0
            self.net_weight_lbl.configure(text=f"NET WT: {nw:,.2f} QTL")
            
            # 2. Brokerage & Remaining Bags Logic
            ent_bags = safe_int(self.total_bags)
            tot_items_bags = sum(safe_int(r['bags']) for r in self.item_rows)
            remaining = ent_bags - tot_items_bags
            
            # FEATURE: Update Allocation Label Status
            if remaining == 0 and ent_bags > 0:
                self.alloc_lbl.configure(text="✔ ALL BAGS ALLOCATED", text_color="green")
            elif remaining > 0:
                self.alloc_lbl.configure(text=f"⚠ REMAINING TO ALLOCATE: {remaining}", text_color="orange")
            elif remaining < 0:
                self.alloc_lbl.configure(text=f"❌ EXCESS BAGS: {abs(remaining)}", text_color="red")
            else:
                self.alloc_lbl.configure(text="(Enter Total Bags)", text_color="gray")

            # FEATURE: Auto Brokerage Calc (Based on Item Share)
            calc_brok = 0
            if tot_items_bags > 0 and nw > 0:
                for r in self.item_rows:
                    brok_rate = self.paddy_data.get(r["type"].get(), 0)
                    wt_share = (safe_int(r['bags']) / tot_items_bags) * nw
                    calc_brok += wt_share * brok_rate
            
            # Only update if user hasn't manually edited (optional, here we force update)
            self.brokerage.delete(0, 'end'); self.brokerage.insert(0, f"{calc_brok:.0f}")
            
        except: pass

    def auto_add_row(self, event):
        self.add_item_row(); self.item_rows[-1]['type'].focus_set(); return "break"

    def setup_navigation(self):
        ws_header = [self.date, self.party, self.lorry, self.total_bags, self.w1, self.w2, self.w3, 
                     self.discount, self.hamali, self.brokerage, self.others_a, self.others_d]
        
        for i, w in enumerate(ws_header):
            next_w = self.item_rows[0]['type'] if self.item_rows and i == len(ws_header) - 1 else ws_header[i+1] if i < len(ws_header)-1 else self.add_btn
            w.bind("<Return>", lambda e, n=next_w: (n.focus_set(), "break")[1])
            w.bind("<Tab>", lambda e, n=next_w: (n.focus_set(), "break")[1])

        for i, row in enumerate(self.item_rows):
            row['type'].bind("<Return>", lambda e, n=row['bags']: (n.focus_set(), "break")[1])
            row['bags'].bind("<Return>", lambda e, n=row['moist']: (n.focus_set(), "break")[1])
            row['moist'].bind("<Return>", lambda e, n=row['rate']: (n.focus_set(), "break")[1])
            if i == len(self.item_rows) - 1: row['rate'].bind("<Return>", self.auto_add_row)
            else: row['rate'].bind("<Return>", lambda e, n=self.item_rows[i+1]['type']: (n.focus_set(), "break")[1])

        self.add_btn.bind("<Return>", lambda e: self.add_item_row())
        self.save_btn.bind("<Return>", lambda e: self.process_bill())

    # --- SHARED CALCULATION LOGIC FOR PREVIEW AND SAVE ---
    def get_bill_data(self):
        try:
            s_float = lambda e: float(e.get()) if e.get().strip() else 0.0
            s_int = lambda e: int(e.get()) if e.get().strip() else 0
            
            b_no = s_int(self.bill_no) 
            weights = [s_float(self.w1), s_float(self.w2), s_float(self.w3)]
            final_w = min([w for w in weights if w > 0]) if any(w > 0 for w in weights) else 0.0
            
            tot_bags = s_int(self.total_bags)
            calc_gross = 0
            items_data = []
            
            tot_bags_items = sum(s_int(r['bags']) for r in self.item_rows)
            # Allocation logic
            dist_bags = tot_bags_items if tot_bags_items > 0 else (tot_bags if tot_bags > 0 else 1)

            for r in self.item_rows:
                bags = s_int(r['bags'])
                rate = s_float(r['rate'])
                moist = s_float(r['moist'])
                deduct = (moist - 14) if moist > 14 else 0
                calc_rate = rate * (1 - (deduct / 100))
                wt = (bags / dist_bags) * final_w
                amt = int(round(wt * calc_rate))
                calc_gross += amt
                
                items_data.append({
                    "paddy_type": r["type"].get().upper(),
                    "bags": bags,
                    "moisture": moist,
                    "base_rate": rate,
                    "calculated_rate": calc_rate,
                    "calculated_weight_kg": wt,
                    "item_amount": amt
                })

            disc = int(round((calc_gross * s_float(self.discount)) / 100))
            net = int(round((calc_gross - disc) + s_float(self.brokerage) + s_float(self.hamali) + s_float(self.others_a)))

            header = {
                "bill_no": b_no, "party_name": self.party.get().upper(), "bill_date": self.date.get(), 
                "date": self.date.get(), "lorry_no": self.lorry.get().upper(), "total_bags": tot_bags, 
                "truck_weight1_kg": s_float(self.w1), "truck_weight2_kg": s_float(self.w2), 
                "truck_weight3_kg": s_float(self.w3), "final_truck_weight_kg": final_w,
                "total_gross_amount": calc_gross, "discount_percent": s_float(self.discount), 
                "brokerage": s_float(self.brokerage), "hamali": s_float(self.hamali), 
                "others_desc": self.others_d.get().upper(), "others_amount": s_float(self.others_a),
                "net_payable": net
            }
            return header, items_data
        except Exception as e:
            messagebox.showerror("Error", f"Calculation Error: {str(e)}")
            return None, None

    def preview_bill(self):
        header, items = self.get_bill_data()
        if not header: return
        if not header["party_name"]: return messagebox.showerror("Error", "Party Name Required")
        
        if pdf_generator.generate_bill_pdf({"header": header, "items": items}):
            file_name = f"BILL-{header['bill_no']}-{header['party_name']}.pdf".upper()
            os.startfile(file_name)
        else:
            messagebox.showerror("Error", "Preview Failed")

    def process_bill(self):
        header, items = self.get_bill_data()
        if not header: return
        if not header["party_name"]: return messagebox.showerror("Error", "PARTY NAME REQUIRED")
        if header["total_bags"] == 0: return messagebox.showerror("Error", "Total Bags 0")
        
        try:
            res = database.add_bill(header, items)
            if isinstance(res, int):
                # Fetch full data to ensure PDF is perfect
                saved_bill = database.get_bill_details(res)
                if pdf_generator.generate_bill_pdf(saved_bill): 
                    messagebox.showinfo("SUCCESS", f"BILL #{res} SAVED & PDF GENERATED!")
                else: 
                    messagebox.showwarning("WARNING", "PDF FAILED")
                self.clear_form()
            else: 
                messagebox.showerror("DB ERROR", res)
        except Exception as e: messagebox.showerror("ERROR", str(e))

    def clear_form(self):
        # Refresh ID
        self.bill_no.configure(state="normal")
        self.bill_no.delete(0, 'end'); self.bill_no.insert(0, str(database.get_next_bill_number()))
        self.bill_no.configure(state="readonly")
        
        for e in [self.party, self.lorry, self.total_bags, self.others_d]: e.delete(0, 'end')
        for e in [self.w1, self.w2, self.w3, self.discount, self.hamali, self.others_a, self.brokerage]: e.delete(0, 'end'); e.insert(0, "0")
        
        while len(self.item_rows) > 1: self.remove_row(self.item_rows[-1])
        r = self.item_rows[0]; [w.delete(0, 'end') for w in [r['type'], r['bags'], r['moist'], r['rate']]]
        self.update_totals()