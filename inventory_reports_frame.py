import customtkinter as ctk
from tkinter import ttk, messagebox
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import database

# --- THEME COLORS ---
THEME_COLOR = "#1f6aa5"
THEME_TEXT = "white"

class InventoryReportsFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.df_summary = pd.DataFrame()
        
        # --- TITLE ---
        ctk.CTkLabel(self, text="INVENTORY INTELLIGENCE", font=("Arial", 20, "bold"), text_color=THEME_COLOR).pack(pady=(10,5), anchor="w", padx=20)

        # --- KPI CARDS ---
        kpi_frame = ctk.CTkFrame(self, fg_color="transparent")
        kpi_frame.pack(fill="x", padx=10, pady=10)
        self.k_stock = self.create_kpi_card(kpi_frame, "CURRENT STOCK (QTL)", "0.00")
        self.k_bags = self.create_kpi_card(kpi_frame, "TOTAL BAGS", "0")
        self.k_value = self.create_kpi_card(kpi_frame, "EST. VALUE (Rs)", "0", highlight=True)

        # --- TABS ---
        self.tabview = ctk.CTkTabview(self, width=1100, height=600)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.tab_stock = self.tabview.add("  LIVE STOCK SNAPSHOT  ")
        self.tab_ledger = self.tabview.add("  STOCK LEDGER (HISTORY)  ")
        
        self.setup_stock_tab()
        self.setup_ledger_tab()
        
        # Initial Load
        self.load_inventory_data()

    def create_kpi_card(self, parent, title, value, highlight=False):
        bg = THEME_COLOR if highlight else ("gray85", "gray16")
        fg = "white"
        card = ctk.CTkFrame(parent, fg_color=bg, corner_radius=10)
        card.pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkLabel(card, text=title, font=("Arial", 11, "bold"), text_color=fg).pack(pady=(15,0))
        lbl = ctk.CTkLabel(card, text=value, font=("Arial", 24, "bold"), text_color=fg)
        lbl.pack(pady=(0,15))
        return lbl

    def setup_stock_tab(self):
        # 1. Chart Area
        self.chart_frame = ctk.CTkFrame(self.tab_stock, fg_color=("gray90", "gray13"), height=250)
        self.chart_frame.pack(fill="x", padx=10, pady=10)
        
        # 2. Table Area
        cols = ["VARIETY", "PURCHASED (IN)", "SOLD (OUT)", "CURRENT STOCK (QTL)", "BAGS BAL.", "AVG RATE", "EST. VALUE"]
        self.tree_stock = ttk.Treeview(self.tab_stock, columns=cols, show="headings", height=12)
        
        for c in cols: 
            self.tree_stock.heading(c, text=c)
            self.tree_stock.column(c, width=120, anchor="center")
            
        self.tree_stock.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkButton(self.tab_stock, text="REFRESH DATA", command=self.load_inventory_data, fg_color=THEME_COLOR, height=40).pack(pady=10)

    def setup_ledger_tab(self):
        f = ctk.CTkFrame(self.tab_ledger, fg_color="transparent")
        f.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(f, text="FILTER VARIETY:").pack(side="left", padx=5)
        self.filter_var = ctk.CTkOptionMenu(f, values=["ALL"], command=self.load_ledger_data)
        self.filter_var.pack(side="left", padx=5)
        
        cols = ["DATE", "TYPE", "REF ID", "VARIETY", "BAGS CHANGE", "WEIGHT CHANGE (KG)"]
        self.tree_ledger = ttk.Treeview(self.tab_ledger, columns=cols, show="headings", height=18)
        
        for c in cols: 
            self.tree_ledger.heading(c, text=c)
            self.tree_ledger.column(c, width=120, anchor="center")
            
        self.tree_ledger.pack(fill="both", expand=True, padx=10, pady=10)

    def load_inventory_data(self):
        # 1. Summary Data
        self.df_summary = database.get_inventory_summary()
        
        # Reset KPIs
        if not self.df_summary.empty:
            # Rounding to 2 decimal places for display
            total_stock_qtl = self.df_summary['current_stock_kg'].sum() / 100
            self.k_stock.configure(text=f"{total_stock_qtl:,.2f}") 
            self.k_bags.configure(text=f"{self.df_summary['current_bags'].sum():,.0f}")
            self.k_value.configure(text=f"Rs {self.df_summary['stock_value'].sum():,.0f}")
        
        # Clear & Fill Table
        self.tree_stock.delete(*self.tree_stock.get_children())
        for _, r in self.df_summary.iterrows():
            self.tree_stock.insert("", "end", values=[
                r['paddy_type'],
                f"{r['total_in_kg']/100:,.2f}",   # Rounded
                f"{r['total_out_kg']/100:,.2f}",  # Rounded
                f"{r['current_stock_kg']/100:,.2f}", # Rounded
                f"{r['current_bags']:,.0f}",
                f"{r['avg_rate']:,.2f}",
                f"{r['stock_value']:,.0f}"
            ])
            
        # Update Chart
        self.update_chart()
        
        # Update Ledger Filter
        if not self.df_summary.empty:
            vars = ["ALL"] + list(self.df_summary['paddy_type'].unique())
            self.filter_var.configure(values=vars)
            
        self.load_ledger_data()

    def update_chart(self):
        for w in self.chart_frame.winfo_children(): w.destroy()
        if self.df_summary.empty: return
        
        fig = Figure(figsize=(6, 2.5), dpi=100, facecolor="#2b2b2b")
        ax = fig.add_subplot(111)
        ax.set_facecolor("#2b2b2b")
        
        # Only graph positive stock
        df_chart = self.df_summary[self.df_summary['current_stock_kg'] > 0]
        
        x = df_chart['paddy_type']
        y = df_chart['current_stock_kg'] / 100 # Qtl
        
        bars = ax.bar(x, y, color=THEME_COLOR, alpha=0.8)
        ax.bar_label(bars, fmt='%.1f', padding=3, color='white', fontsize=9)
        
        ax.set_title("CURRENT STOCK HOLDING (QTL)", color="white", fontsize=10, pad=10)
        ax.tick_params(axis='x', colors='white', labelsize=8)
        ax.tick_params(axis='y', colors='white', labelsize=8)
        ax.spines['bottom'].set_color('white')
        ax.spines['top'].set_color('none')
        ax.spines['left'].set_color('none')
        ax.spines['right'].set_color('none')
        ax.yaxis.set_visible(False) 
        
        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def load_ledger_data(self, filter_val=None):
        val = self.filter_var.get()
        df = database.get_inventory_ledger(val)
        self.tree_ledger.delete(*self.tree_ledger.get_children())
        
        for _, r in df.iterrows():
            self.tree_ledger.insert("", "end", values=[
                r['date'],
                r['type'],
                r['ref_id'],
                r['paddy_type'],
                f"{r['bags_change']:,.0f}",      # No decimals for bags
                f"{r['weight_change_kg']:,.2f}"  # Max 2 decimals for weight
            ])