import customtkinter as ctk
from tkinter import ttk, messagebox
import database
import pdf_generator
import sales_pdf_generator
import os

class AllBillsFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        
        # --- HEADER ---
        ctk.CTkLabel(self, text="TRANSACTION ARCHIVE", font=("Arial", 22, "bold")).pack(pady=(0, 20), anchor="w")

        # --- SEARCH BAR ---
        search_frame = ctk.CTkFrame(self)
        search_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(search_frame, text="Search (ID or Party Name):", font=("Arial", 12)).pack(side="left", padx=15, pady=15)
        
        self.search_entry = ctk.CTkEntry(search_frame, width=250)
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<Return>", lambda e: self.load_data()) # Press Enter to search
        
        ctk.CTkButton(search_frame, text="Search", command=self.load_data, width=100, fg_color="#1f538d").pack(side="left", padx=15)
        
        # Filter Dropdown
        self.filter_var = ctk.CTkComboBox(search_frame, values=["ALL", "PURCHASE", "SALE"], width=120, command=lambda x: self.load_data())
        self.filter_var.pack(side="right", padx=15)
        self.filter_var.set("ALL")

        # --- DATA GRID (Standard Table) ---
        table_frame = ctk.CTkFrame(self)
        table_frame.pack(fill="both", expand=True, pady=10)
        
        # Table Style
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", rowheight=28, font=("Arial", 11), background="#2b2b2b", foreground="white", fieldbackground="#2b2b2b", borderwidth=0)
        style.configure("Treeview.Heading", font=("Arial", 11, "bold"), background="#333", foreground="white", relief="flat")
        style.map("Treeview", background=[('selected', '#1f538d')])

        cols = ("TYPE", "ID", "DATE", "PARTY NAME", "TOTAL BAGS", "NET AMOUNT")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=15)
        
        # Configure Columns
        self.tree.heading("TYPE", text="TYPE"); self.tree.column("TYPE", width=100, anchor="center")
        self.tree.heading("ID", text="ID"); self.tree.column("ID", width=80, anchor="center")
        self.tree.heading("DATE", text="DATE"); self.tree.column("DATE", width=100, anchor="center")
        self.tree.heading("PARTY NAME", text="PARTY NAME"); self.tree.column("PARTY NAME", width=250, anchor="w")
        self.tree.heading("TOTAL BAGS", text="TOTAL BAGS"); self.tree.column("TOTAL BAGS", width=100, anchor="center")
        self.tree.heading("NET AMOUNT", text="NET AMOUNT"); self.tree.column("NET AMOUNT", width=120, anchor="e")
            
        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y", padx=(0, 5), pady=5)
        self.tree.pack(fill="both", expand=True, padx=(5, 0), pady=5)

        # --- ACTION BUTTONS ---
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", pady=20)
        
        # "Open PDF" Button (Green)
        ctk.CTkButton(btn_frame, text="OPEN PDF / PRINT", command=self.open_bill, fg_color="#2cc985", text_color="white", width=200, height=45, font=("Arial", 12, "bold")).pack(side="right")
        
        # "Refresh" Button (Dark Gray)
        ctk.CTkButton(btn_frame, text="REFRESH LIST", command=self.load_data, fg_color="#444", width=150, height=45).pack(side="right", padx=10)

    def on_show(self):
        """Called when this frame is selected from the menu"""
        self.load_data()

    def load_data(self):
        """Fetches data from DB and populates the table"""
        query = self.search_entry.get().lower()
        filter_type = self.filter_var.get()
        
        # Clear existing data
        self.tree.delete(*self.tree.get_children())
        
        conn = database.sqlite3.connect(database.DATABASE_FILE)
        cursor = conn.cursor()
        
        records = []
        
        # 1. Fetch Purchases (Bills)
        if filter_type in ["ALL", "PURCHASE"]:
            try:
                # Note: We only select columns that definitely exist to avoid errors
                cursor.execute("SELECT b.bill_no, b.bill_date, p.party_name, b.total_bags, b.net_payable FROM bills b JOIN parties p ON b.party_id = p.party_id")
                for r in cursor.fetchall():
                    if query in str(r[0]).lower() or query in str(r[2]).lower():
                        records.append(("PURCHASE", r[0], r[1], r[2], r[3], r[4]))
            except Exception as e:
                print(f"Error fetching purchases: {e}")

        # 2. Fetch Sales (Sales Bills)
        if filter_type in ["ALL", "SALE"]:
            try:
                cursor.execute("SELECT b.bill_no, b.bill_date, p.party_name, b.total_bags, b.net_payable FROM sales_bills b JOIN parties p ON b.party_id = p.party_id")
                for r in cursor.fetchall():
                    if query in str(r[0]).lower() or query in str(r[2]).lower():
                        records.append(("SALE", r[0], r[1], r[2], r[3], r[4]))
            except Exception as e:
                print(f"Error fetching sales: {e}")
        
        conn.close()
        
        # Sort by Date (Newest first)
        records.sort(key=lambda x: x[2], reverse=True)
        
        # Insert into table with color coding
        for r in records:
            # Format Amount with Currency Symbol
            formatted_amt = f"₹ {r[5]:,.0f}"
            
            # Apply tags for color
            tag = "purchase" if r[0] == "PURCHASE" else "sale"
            
            self.tree.insert("", "end", values=(r[0], r[1], r[2], r[3], r[4], formatted_amt), tags=(tag,))
        
        # Define Colors
        self.tree.tag_configure("purchase", foreground="#4fc3f7") # Light Blue for Purchase
        self.tree.tag_configure("sale", foreground="#2CC985")    # Green for Sales

    def open_bill(self):
        """Opens the PDF for the selected bill"""
        item = self.tree.selection()
        if not item:
            messagebox.showinfo("Info", "Please select a record to open.")
            return
            
        vals = self.tree.item(item[0])['values']
        bill_type = vals[0]
        bill_no = vals[1]
        party_name = vals[3]
        
        try:
            if bill_type == "PURCHASE":
                data = database.get_bill_details(bill_no)
                if data and pdf_generator.generate_bill_pdf(data):
                    os.startfile(f"BILL-{bill_no}-{party_name}.pdf".upper())
            else:
                data = database.get_sales_bill_details(bill_no)
                if data and sales_pdf_generator.generate_sales_pdf(data):
                    os.startfile(f"SALE-{bill_no}-{party_name}.pdf".upper())
                    
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file: {str(e)}")