import customtkinter as ctk
from tkinter import messagebox, Toplevel, ttk
from tkcalendar import Calendar
from datetime import datetime
import database
import pandas as pd

# --- Calm Blue Theme ---
THEME_COLOR = "#1f6aa5"
THEME_HOVER = "#144d7a"

class ProcessingFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure((0, 1), weight=1, uniform="a")
        self.grid_rowconfigure(3, weight=1)
        self.item_rows = []
        self.original_stock_data = {} # Stores { 'IR64': {bags: 100, avg: 50.5}, ... }
        
        # --- TITLE ---
        ctk.CTkLabel(self, text="PADDY PROCESSING (BATCH ENTRY)", font=("Arial", 22, "bold"), text_color=THEME_COLOR).grid(row=0, column=0, columnspan=2, pady=(0,20))

        # --- LEFT CARD: BATCH INFO ---
        c1 = ctk.CTkFrame(self, fg_color=("gray90", "gray13"), corner_radius=10)
        c1.grid(row=1, column=0, padx=15, pady=10, sticky="nsew")
        ctk.CTkLabel(c1, text="BATCH INFO", font=("Arial", 14, "bold")).pack(pady=15)
        
        f_date = ctk.CTkFrame(c1, fg_color="transparent")
        f_date.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(f_date, text="DATE:", width=100, anchor="w", font=("Arial",12,"bold")).pack(side="left")
        self.date_entry = ctk.CTkEntry(f_date, height=35)
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.date_entry.pack(side="right", fill="x", expand=True)
        self.date_entry.bind("<Button-1>", self.open_cal)
        
        self.batch_lbl = ctk.CTkLabel(c1, text="BATCH NO: (AUTO)", font=("Arial", 16, "bold"), text_color=THEME_COLOR)
        self.batch_lbl.pack(pady=20)
        
        # --- RIGHT CARD: INPUTS ---
        c2 = ctk.CTkFrame(self, fg_color=("gray90", "gray13"), corner_radius=10)
        c2.grid(row=1, column=1, padx=15, pady=10, sticky="nsew")
        ctk.CTkLabel(c2, text="CONSUMPTION LIST", font=("Arial", 14, "bold")).pack(pady=5)
        
        self.items_frame = ctk.CTkScrollableFrame(c2, fg_color="transparent", height=180)
        self.items_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.add_btn = ctk.CTkButton(c2, text="+ ADD VARIETY", command=self.add_item_row, width=150, fg_color=THEME_COLOR, hover_color=THEME_HOVER, font=ctk.CTkFont(weight="bold"))
        self.add_btn.pack(pady=5)
        
        self.total_lbl = ctk.CTkLabel(c2, text="TOTAL INPUT: 0 Bags | 0.00 QTL", font=("Arial", 14, "bold"), text_color=THEME_COLOR)
        self.total_lbl.pack(pady=15)

        # --- SUBMIT BUTTON ---
        self.save_btn = ctk.CTkButton(self, text="START BATCH PROCESS", fg_color=THEME_COLOR, hover_color=THEME_HOVER, height=50, width=300, font=("Arial", 16, "bold"), command=self.save_batch)
        self.save_btn.grid(row=2, column=0, columnspan=2, pady=(10, 20))

        # --- LIVE STOCK TABLE ---
        table_frame = ctk.CTkFrame(self, fg_color=("gray90", "gray13"), corner_radius=10)
        table_frame.grid(row=3, column=0, columnspan=2, padx=15, pady=(0, 15), sticky="nsew")
        
        ctk.CTkLabel(table_frame, text="LIVE STOCK SIMULATION (AFTER DEDUCTION)", font=("Arial", 14, "bold"), text_color=THEME_COLOR).pack(pady=(15,10))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#2b2b2b", foreground="white", fieldbackground="#2b2b2b", borderwidth=0, font=("Arial", 11))
        style.configure("Treeview.Heading", background=THEME_COLOR, foreground="white", font=("Arial", 11, "bold"), borderwidth=0)
        
        cols = ["VARIETY", "ORIGINAL BAGS", "INPUT BAGS", "REMAINING BAGS", "AVG WT (KG)"]
        self.stock_tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="none", height=6)
        
        for c in cols:
            self.stock_tree.heading(c, text=c)
            self.stock_tree.column(c, anchor="center", width=150)
            
        self.stock_tree.pack(fill="both", expand=True, padx=10, pady=10)

    def on_show(self):
        # 1. Batch No
        b_no, err = database.get_next_batch_number(self.date_entry.get())
        self.batch_lbl.configure(text=f"NEXT BATCH: {b_no}" if not err else err)
        
        # 2. Load Real Inventory Snapshot
        self.load_original_stock()
        
        # 3. Reset UI
        if not self.item_rows: self.add_item_row()
        self.live_update() # Initial render

    def load_original_stock(self):
        """Fetches DB stock once and stores it for live subtraction."""
        self.original_stock_data = {}
        df = database.get_inventory_summary()
        if not df.empty:
            for _, r in df.iterrows():
                if r['current_bags'] > 0:
                    self.original_stock_data[r['paddy_type']] = {
                        'bags': int(r['current_bags']),
                        'avg': r['avg_rate']
                    }

    def open_cal(self, e):
        top = Toplevel(self); cal = Calendar(top, date_pattern='y-mm-dd'); cal.pack(pady=10)
        ctk.CTkButton(top, text="SELECT", command=lambda: [self.date_entry.delete(0,'end'), self.date_entry.insert(0, cal.get_date()), self.on_show(), top.destroy()]).pack(pady=10)

    def add_item_row(self):
        row = ctk.CTkFrame(self.items_frame, fg_color=("gray85", "gray20"))
        row.pack(fill="x", pady=4)
        
        vars = [v[1] for v in database.get_all_paddy_varieties()]
        
        var_menu = ctk.CTkOptionMenu(row, values=vars, width=180, fg_color=THEME_COLOR, button_color=THEME_HOVER, command=lambda x: self.live_update())
        var_menu.pack(side="left", padx=5, pady=5)
        if vars: var_menu.set(vars[0])
        
        bags_ent = ctk.CTkEntry(row, width=100, placeholder_text="BAGS")
        bags_ent.pack(side="left", padx=5, pady=5)
        bags_ent.bind("<KeyRelease>", self.live_update) # TRIGGER LIVE UPDATE
        
        # Label to show "Avail - Input = Rem | Avg Rate"
        stock_lbl = ctk.CTkLabel(row, text="", font=("Arial", 11), text_color="gray", width=280, anchor="w")
        stock_lbl.pack(side="left", padx=10)
        
        btn = ctk.CTkButton(row, text="X", width=40, fg_color="#D32F2F", hover_color="#C62828", command=lambda: self.remove_row(row_dict))
        btn.pack(side="right", padx=5)
        
        row_dict = {"frame": row, "var": var_menu, "bags": bags_ent, "lbl": stock_lbl}
        self.item_rows.append(row_dict)
        self.live_update()

    def remove_row(self, rd):
        if len(self.item_rows) > 1:
            rd["frame"].destroy()
            self.item_rows.remove(rd)
            self.live_update()

    def live_update(self, e=None):
        """Calculates Remaining Stock LIVE and Updates Table & Labels."""
        
        # 1. Tally up User Inputs
        user_input_map = {} 
        total_bags_input = 0
        total_qtl_input = 0
        
        for r in self.item_rows:
            v = r['var'].get()
            try: b = int(r['bags'].get())
            except: b = 0
            
            user_input_map[v] = user_input_map.get(v, 0) + b
            total_bags_input += b
            
            # Avg Weight Calc
            avg = self.original_stock_data.get(v, {}).get('avg', 0)
            total_qtl_input += (b * avg) / 100

        # 2. Update Row Labels (Avail - Input = Rem | Avg Rate)
        for r in self.item_rows:
            v = r['var'].get()
            try: current_input = int(r['bags'].get())
            except: current_input = 0
            
            orig = self.original_stock_data.get(v, {}).get('bags', 0)
            avg = self.original_stock_data.get(v, {}).get('avg', 0)
            
            rem = orig - user_input_map.get(v, 0) 
            
            # Label Construction
            avg_text = f"Avg: {avg:.2f} kg"
            
            if rem < 0:
                # Even in error, show the average!
                r['lbl'].configure(text=f"❌ Deficit: {abs(rem)} | {avg_text}", text_color="red")
            elif current_input > 0:
                # Active Input
                r['lbl'].configure(text=f"Avail: {orig} - {user_input_map.get(v,0)} = {rem} Rem | {avg_text}", text_color="lightgreen")
            else:
                # Idle State
                r['lbl'].configure(text=f"Avail: {orig} Bags | {avg_text}", text_color="gray")

        # 3. Update Total Label
        self.total_lbl.configure(text=f"TOTAL INPUT: {total_bags_input} Bags | {total_qtl_input:,.2f} QTL")

        # 4. Refresh Stock Table
        self.stock_tree.delete(*self.stock_tree.get_children())
        
        for variety, data in self.original_stock_data.items():
            orig = data['bags']
            avg = data['avg']
            deduction = user_input_map.get(variety, 0)
            final_rem = orig - deduction
            
            tag = "normal"
            if deduction > 0: tag = "active"
            if final_rem < 0: tag = "error"
            
            self.stock_tree.insert("", "end", values=[
                variety,
                orig,
                deduction if deduction > 0 else "-",
                final_rem,
                f"{avg:.2f}"
            ], tags=(tag,))

        self.stock_tree.tag_configure("active", background="#2b4b2b") 
        self.stock_tree.tag_configure("error", background="#4b2b2b")

    def save_batch(self):
        date = self.date_entry.get()
        items_data = []
        
        for r in self.item_rows:
            try: b = int(r["bags"].get())
            except: continue
            if b > 0: items_data.append({'paddy_type': r["var"].get(), 'bags': b})
            
        if not items_data:
            messagebox.showerror("Error", "Enter bags to process.")
            return
            
        msg = database.add_processing_batch(date, items_data)
        if "Success" in msg:
            messagebox.showinfo("Success", msg)
            for r in self.item_rows: r["frame"].destroy()
            self.item_rows = []
            self.on_show()
        else:
            messagebox.showerror("Error", msg)