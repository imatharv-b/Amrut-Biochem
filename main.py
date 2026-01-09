import customtkinter as ctk
from tkinter import messagebox
from billing_frame import BillingFrame
from edit_bill_frame import EditBillFrame
from sales_billing_frame import SalesBillingFrame
from processing_frame import ProcessingFrame 
from inventory_reports_frame import InventoryReportsFrame
from processing_reports_frame import ProcessingReportsFrame 
from market_analysis_frame import MarketAnalysisFrame 
from business_intelligence_frame import BusinessIntelligenceFrame
from reports_frame import ReportsFrame
from masters_frame import MastersFrame
from paddy_master_frame import PaddyMasterFrame
from party_dashboard_frame import PartyDashboardFrame
from all_bills_frame import AllBillsFrame 
import database

# --- STANDARD THEME ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

class LoginApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Login - KESAR INDUSTRIES ERP")
        self.geometry("400x300")
        self.resizable(False, False)
        self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(0, weight=1)
        
        self.frame = ctk.CTkFrame(self, width=300, height=200, corner_radius=10)
        self.frame.place(relx=0.5, rely=0.5, anchor="center")
        
        ctk.CTkLabel(self.frame, text="SYSTEM LOGIN", font=("Arial", 20, "bold")).pack(pady=20)
        self.username = ctk.CTkEntry(self.frame, placeholder_text="Username", width=200)
        self.username.pack(pady=10)
        self.password = ctk.CTkEntry(self.frame, placeholder_text="Password", show="*", width=200)
        self.password.pack(pady=10)
        self.login_btn = ctk.CTkButton(self.frame, text="LOGIN", command=self.check_login, width=200)
        self.login_btn.pack(pady=20)
        
        self.username.bind("<Return>", lambda e: self.password.focus_set())
        self.password.bind("<Return>", lambda e: self.check_login())
        self.login_btn.bind("<Return>", lambda e: self.check_login())

    def check_login(self):
        if self.username.get() == "kesar" and self.password.get() == "aditya123":
            self.destroy(); app = MainApp(); app.mainloop()
        else: messagebox.showerror("Login Failed", "Invalid Username or Password")

class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("KESAR INDUSTRIES - ERP System")
        self.geometry("1280x900")
        self.grid_rowconfigure(0, weight=1); self.grid_columnconfigure(1, weight=1)
        
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=("gray95", "gray10"))
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(15, weight=1)
        
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.grid(row=0, column=0, padx=20, pady=(30, 30))
        ctk.CTkLabel(logo_frame, text="KESAR\nINDUSTRIES", font=ctk.CTkFont(size=22, weight="bold")).pack()
        ctk.CTkLabel(logo_frame, text="ERP System", font=ctk.CTkFont(size=12)).pack()

        # NAVIGATION
        self.btn_billing = self.create_nav_btn("  BILLING ENTRY", "billing", 1)
        self.btn_sales = self.create_nav_btn("  SELLING ENTRY", "sales", 2)
        self.btn_edit = self.create_nav_btn("  EDIT OLD BILLS", "edit_bill", 3)
        self.btn_all_bills = self.create_nav_btn("  ALL BILLS & ARCHIVE", "all_bills", 4) # <--- New Button
        
        self.create_divider(5)
        
        self.btn_proc = self.create_nav_btn("  PROCESSING (BATCH)", "processing", 6)
        self.btn_proc_rep = self.create_nav_btn("  PROCESSING REPORTS", "processing_rep", 7)
        self.btn_inv = self.create_nav_btn("  INVENTORY REPORTS", "inventory", 8)
        self.btn_market = self.create_nav_btn("  MARKET INTELLIGENCE", "market", 9)
        self.btn_bi = self.create_nav_btn("  ★ BI & INSIGHTS", "bi_insights", 10)
        
        self.create_divider(11)
        
        self.btn_reports = self.create_nav_btn("  FINANCIAL REPORTS", "reports", 12)
        self.btn_party = self.create_nav_btn("  PARTY MASTERS", "party_masters", 13)
        self.btn_paddy = self.create_nav_btn("  PADDY MASTERS", "paddy_masters", 14)
        
        # Main Area
        self.main_area = ctk.CTkFrame(self, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=25, pady=25)
        self.main_area.grid_rowconfigure(0, weight=1)
        self.main_area.grid_columnconfigure(0, weight=1)

        self.frames = {
            "billing": BillingFrame(self.main_area),
            "sales": SalesBillingFrame(self.main_area),
            "edit_bill": EditBillFrame(self.main_area),
            "all_bills": AllBillsFrame(self.main_area), # <--- New Frame
            "processing": ProcessingFrame(self.main_area),
            "processing_rep": ProcessingReportsFrame(self.main_area),
            "inventory": InventoryReportsFrame(self.main_area),
            "market": MarketAnalysisFrame(self.main_area),
            "bi_insights": BusinessIntelligenceFrame(self.main_area),
            "reports": ReportsFrame(self.main_area),
            "party_masters": MastersFrame(self.main_area),
            "paddy_masters": PaddyMasterFrame(self.main_area),
            "party_dashboard": PartyDashboardFrame(self.main_area)
        }
        self.select_frame("billing")

    def create_divider(self, row):
        ctk.CTkFrame(self.sidebar, height=2, fg_color="gray30").grid(row=row, column=0, sticky="ew", padx=20, pady=10)

    def create_nav_btn(self, text, name, row):
        btn = ctk.CTkButton(self.sidebar, text=text, height=45, command=lambda: self.select_frame(name), 
                            fg_color="transparent", text_color=("gray10", "gray90"), 
                            hover_color=("gray70", "gray20"), anchor="w", font=ctk.CTkFont(size=14, weight="bold"))
        btn.grid(row=row, column=0, padx=10, pady=5, sticky="ew")
        return btn

    def select_frame(self, name, **kwargs):
        btns = [
            ("billing", self.btn_billing), ("sales", self.btn_sales), ("edit_bill", self.btn_edit), ("all_bills", self.btn_all_bills),
            ("processing", self.btn_proc), ("processing_rep", self.btn_proc_rep),
            ("inventory", self.btn_inv), ("market", self.btn_market), ("bi_insights", self.btn_bi),
            ("reports", self.btn_reports), ("party_masters", self.btn_party), ("paddy_masters", self.btn_paddy)
        ]
        
        for n, b in btns: 
            color = "#1f538d" if n == "bi_insights" and name == n else ctk.ThemeManager.theme["CTkButton"]["fg_color"]
            b.configure(fg_color=color if name == n else "transparent", text_color="white" if name == n else ("gray10", "gray90"))
        
        for f in self.frames.values(): f.grid_forget()
        f = self.frames[name]; f.grid(row=0, column=0, sticky="nsew")
        
        if hasattr(f, 'on_show'): f.on_show()
        elif hasattr(f, 'load_data'): f.load_data()
        elif hasattr(f, 'refresh_data'): f.refresh_data()
        elif hasattr(f, 'load_inventory_data'): f.load_inventory_data()
        elif hasattr(f, 'load_insights'): f.load_insights()
        elif hasattr(f, 'refresh_party_list'): f.refresh_party_list()
        elif hasattr(f, 'refresh_variety_list'): f.refresh_variety_list()
        elif hasattr(f, 'load_party_data') and "party_id" in kwargs: f.load_party_data(kwargs["party_id"])

    def load_bill_for_editing(self, bill_no):
        self.select_frame("edit_bill") 
        self.frames["edit_bill"].search_entry.delete(0, 'end')
        self.frames["edit_bill"].search_entry.insert(0, str(bill_no))
        self.frames["edit_bill"].search_bill()

if __name__ == "__main__":
    database.setup_database()
    app = LoginApp()
    app.mainloop()