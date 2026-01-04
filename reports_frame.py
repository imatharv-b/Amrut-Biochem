import customtkinter as ctk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import database
from datetime import date, timedelta
import numpy as np

class ReportsFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.df = pd.DataFrame()
        
        # Main Tabview
        self.tabview = ctk.CTkTabview(self, width=1100, height=800)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.tab_bills = self.tabview.add("  DASHBOARD & BILLS  ")
        self.tab_variety = self.tabview.add("  VARIETY ANALYSIS  ")
        
        self.apply_treeview_style()
        self.setup_bills_tab()
        self.setup_variety_tab()

    def apply_treeview_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#2b2b2b", fieldbackground="#2b2b2b", foreground="white", rowheight=30, font=("Arial", 11))
        style.configure("Treeview.Heading", background="#1f1f1f", foreground="white", font=("Arial", 12, "bold"))
        style.map("Treeview", background=[('selected', '#1f6aa5')])

    # ================= BILLS TAB =================
    def setup_bills_tab(self):
        # 1. Filter Bar
        f1 = ctk.CTkFrame(self.tab_bills, fg_color=("gray90", "gray13"), corner_radius=8)
        f1.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(f1, text="PERIOD:", font=("Arial", 12, "bold")).pack(side="left", padx=(15,5), pady=10)
        self.start = DateEntry(f1, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='y-mm-dd')
        self.start.set_date(date.today()-timedelta(days=30))
        self.start.pack(side="left", padx=5, pady=10)
        
        ctk.CTkLabel(f1, text="TO", font=("Arial", 12, "bold")).pack(side="left", padx=5)
        self.end = DateEntry(f1, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='y-mm-dd')
        self.end.pack(side="left", padx=5, pady=10)
        
        ctk.CTkButton(f1, text="REFRESH DASHBOARD", command=self.load_data, font=("Arial", 12, "bold"), fg_color="#1f6aa5", height=32).pack(side="left", padx=20)

        # 2. KPI Cards
        f2 = ctk.CTkFrame(self.tab_bills, fg_color="transparent")
        f2.pack(fill="x", padx=5, pady=5)
        self.k_bills = self.create_kpi_card(f2, "TOTAL BILLS", "0")
        self.k_weight = self.create_kpi_card(f2, "TOTAL WEIGHT (QTL)", "0.00")
        self.k_amt = self.create_kpi_card(f2, "NET PAYABLE (Rs)", "0")

        # 3. Charts Area (Split 50/50)
        chart_container = ctk.CTkFrame(self.tab_bills, fg_color="transparent")
        chart_container.pack(fill="x", padx=5, pady=5)
        
        self.frame_chart1 = ctk.CTkFrame(chart_container, fg_color=("gray90", "gray13"), corner_radius=10)
        self.frame_chart1.pack(side="left", fill="both", expand=True, padx=(0,5))
        
        self.frame_chart2 = ctk.CTkFrame(chart_container, fg_color=("gray90", "gray13"), corner_radius=10)
        self.frame_chart2.pack(side="right", fill="both", expand=True, padx=(5,0))

        # 4. Detailed Table
        f3 = ctk.CTkFrame(self.tab_bills, fg_color=("gray90", "gray13"), corner_radius=10)
        f3.pack(fill="both", expand=True, padx=5, pady=10)
        ctk.CTkLabel(f3, text="RECENT TRANSACTIONS (DOUBLE CLICK TO EDIT)", font=("Arial", 14, "bold")).pack(anchor="w", padx=15, pady=(10,5))
        
        self.tree = ttk.Treeview(f3, show="headings", height=8)
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        
        # --- BIND DOUBLE CLICK ---
        self.tree.bind("<Double-1>", self.on_bill_double_click)

    # ================= VARIETY TAB =================
    def setup_variety_tab(self):
        # 1. Performance Cards
        f1 = ctk.CTkFrame(self.tab_variety, fg_color="transparent")
        f1.pack(fill="x", padx=5, pady=10)
        self.card_vol = self.create_kpi_card(f1, "HIGHEST VOLUME", "-", color=True)
        self.card_rate = self.create_kpi_card(f1, "HIGHEST RATE", "-", color=True)

        v_charts = ctk.CTkFrame(self.tab_variety, fg_color="transparent")
        v_charts.pack(fill="x", padx=5, pady=5)
        
        self.frame_v_chart1 = ctk.CTkFrame(v_charts, fg_color=("gray90", "gray13"), corner_radius=10)
        self.frame_v_chart1.pack(side="left", fill="both", expand=True, padx=(0,5))
        
        self.frame_v_chart2 = ctk.CTkFrame(v_charts, fg_color=("gray90", "gray13"), corner_radius=10)
        self.frame_v_chart2.pack(side="right", fill="both", expand=True, padx=(5,0))

        f3 = ctk.CTkFrame(self.tab_variety, fg_color=("gray90", "gray13"), corner_radius=10)
        f3.pack(fill="both", expand=True, padx=5, pady=10)
        
        cols = ["VARIETY", "TOTAL WEIGHT (QTL)", "AVG RATE", "AVG MOIST %", "EST. BROKERAGE"]
        self.v_tree = ttk.Treeview(f3, columns=cols, show="headings", height=10)
        for c in cols: 
            self.v_tree.heading(c, text=c)
            self.v_tree.column(c, width=120, anchor="center")
        self.v_tree.pack(fill="both", expand=True, padx=10, pady=10)

    # ================= HELPER FUNCTIONS =================
    def create_kpi_card(self, parent, title, value, color=False):
        if color:
            bg_color = ctk.ThemeManager.theme["CTkButton"]["fg_color"]
            txt_color = "white"
        else:
            bg_color = ("gray85", "gray16")
            txt_color = "white"
        
        card = ctk.CTkFrame(parent, fg_color=bg_color, corner_radius=10)
        card.pack(side="left", fill="x", expand=True, padx=5)
        
        ctk.CTkLabel(card, text=title, font=("Arial", 11, "bold"), text_color=txt_color).pack(pady=(15,0))
        lbl_val = ctk.CTkLabel(card, text=value, font=("Arial", 24, "bold"), text_color=txt_color)
        lbl_val.pack(pady=(0,15))
        return lbl_val

    def embed_chart(self, fig, parent):
        for widget in parent.winfo_children(): widget.destroy()
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    def dark_plot_style(self, ax, title):
        ax.set_facecolor("#2b2b2b")
        ax.tick_params(axis='x', colors='white')
        ax.tick_params(axis='y', colors='white')
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.spines['bottom'].set_color('white')
        ax.spines['top'].set_color('none')
        ax.spines['left'].set_color('white')
        ax.spines['right'].set_color('none')
        ax.set_title(title, color='white', pad=15, fontweight="bold")

    # ================= LOGIC & DATA LOADING =================
    def load_data(self):
        try:
            self.df = database.get_report_data_with_items(self.start.get(), self.end.get())
            
            self.tree.delete(*self.tree.get_children())
            self.v_tree.delete(*self.v_tree.get_children())
            
            if self.df.empty:
                messagebox.showinfo("Report", "No data available for this date range.")
                return

            # --- 1. UPDATE BILLS TAB ---
            df_bills = self.df.drop_duplicates('bill_no')
            
            self.k_bills.configure(text=str(len(df_bills)))
            self.k_weight.configure(text=f"{df_bills['final_truck_weight_kg'].sum():,.2f}")
            self.k_amt.configure(text=f"{df_bills['net_payable'].sum():,.0f}")

            # Define Columns (Added 'bill_total_brokerage')
            cols = ['bill_no', 'bill_date', 'party_name', 'total_bags', 'final_truck_weight_kg', 'bill_total_brokerage', 'net_payable']
            self.tree["columns"] = cols
            
            # Map column names to friendly headers
            headers = {
                'bill_no': 'BILL NO',
                'bill_date': 'BILL DATE',
                'party_name': 'PARTY NAME',
                'total_bags': 'TOTAL BAGS',
                'final_truck_weight_kg': 'FINAL WEIGHT',
                'bill_total_brokerage': 'BROKERAGE', # New Header
                'net_payable': 'NET PAYABLE'
            }
            
            for c in cols: 
                self.tree.heading(c, text=headers.get(c, c.replace('_',' ').upper()))
            
            for _, r in df_bills[cols].iterrows(): 
                vals = list(r)
                # ROUNDING: Index 5 is Brokerage, Index 6 is Net Payable
                vals[5] = f"{vals[5]:.0f}" 
                vals[6] = f"{vals[6]:.0f}"
                self.tree.insert("", "end", values=vals)

            # CHART 1: Top 5 Parties
            fig1 = Figure(figsize=(5, 3), dpi=100, facecolor="#2b2b2b")
            ax1 = fig1.add_subplot(111)
            top_parties = df_bills.groupby('party_name')['net_payable'].sum().nlargest(5).sort_values()
            if not top_parties.empty:
                bars = ax1.barh(top_parties.index, top_parties.values, color="#1f6aa5")
                ax1.bar_label(bars, fmt='{:,.0f}', padding=3, color='white', fontsize=8)
            self.dark_plot_style(ax1, "TOP 5 PARTIES BY PURCHASE")
            self.embed_chart(fig1, self.frame_chart1)

            # CHART 2: Daily Trend
            fig2 = Figure(figsize=(5, 3), dpi=100, facecolor="#2b2b2b")
            ax2 = fig2.add_subplot(111)
            df_bills['bill_date'] = pd.to_datetime(df_bills['bill_date'])
            trend = df_bills.groupby('bill_date')['final_truck_weight_kg'].sum()
            if not trend.empty:
                ax2.plot(trend.index, trend.values, color="#00ffcc", marker="o", linewidth=2)
                ax2.grid(color='gray', linestyle='--', linewidth=0.3, alpha=0.5)
            self.dark_plot_style(ax2, "DAILY WEIGHT TREND (QTL)")
            self.embed_chart(fig2, self.frame_chart2)

            # --- 2. UPDATE VARIETY TAB ---
            self.update_variety_analysis()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load report data:\n{e}")

    def update_variety_analysis(self):
        if self.df.empty: return

        self.df['default_brokerage_rate'] = self.df['default_brokerage_rate'].fillna(0)
        self.df['calc_brokerage'] = self.df['item_weight'] * self.df['default_brokerage_rate']
        self.df['wt_rate'] = self.df['base_rate'] * self.df['item_weight']
        self.df['wt_moist'] = self.df['moisture'] * self.df['item_weight']

        grp = self.df.groupby('paddy_type')
        
        with np.errstate(divide='ignore', invalid='ignore'):
            total_wt = grp['item_weight'].sum()
            avg_rate = grp['wt_rate'].sum() / total_wt
            avg_moist = grp['wt_moist'].sum() / total_wt
            total_brok = grp['calc_brokerage'].sum()

        stats = pd.DataFrame({
            'wt': total_wt,
            'rate': avg_rate.fillna(0),
            'moist': avg_moist.fillna(0),
            'brok': total_brok
        }).reset_index()

        for _, r in stats.iterrows():
            self.v_tree.insert("", "end", values=[
                r['paddy_type'], 
                f"{r['wt']:,.2f}", 
                f"{r['rate']:,.0f}",  # Rounded
                f"{r['moist']:.1f}", 
                f"{r['brok']:,.0f}"   # Rounded
            ])

        if not stats.empty and stats['wt'].sum() > 0:
            best_vol = stats.loc[stats['wt'].idxmax()]
            self.card_vol.configure(text=f"{best_vol['paddy_type']}\n({best_vol['wt']:,.0f} QTL)")
            
            real_rates = stats[stats['wt'] > 0]
            if not real_rates.empty:
                best_rate = real_rates.loc[real_rates['rate'].idxmax()]
                self.card_rate.configure(text=f"{best_rate['paddy_type']}\n(Rs {best_rate['rate']:,.0f})")
        else:
            self.card_vol.configure(text="-")
            self.card_rate.configure(text="-")

        # CHART 3: Donut
        fig3 = Figure(figsize=(5, 3), dpi=100, facecolor="#2b2b2b")
        ax3 = fig3.add_subplot(111)
        if not stats.empty and stats['wt'].sum() > 0:
            ax3.pie(stats['wt'], labels=stats['paddy_type'], autopct='%1.1f%%', 
                    colors=['#1f6aa5', '#ff7f0e', '#2ca02c', '#d62728'], textprops={'color':"white"})
            fig3.gca().add_artist(__import__('matplotlib.patches').patches.Circle((0,0),0.70,fc='#2b2b2b'))
        self.dark_plot_style(ax3, "VOLUME SHARE (QTL)")
        self.embed_chart(fig3, self.frame_v_chart1)

        # CHART 4: Rate Bar
        fig4 = Figure(figsize=(5, 3), dpi=100, facecolor="#2b2b2b")
        ax4 = fig4.add_subplot(111)
        if not stats.empty:
            ax4.bar(stats['paddy_type'], stats['rate'], color="#ff9900", alpha=0.8)
        self.dark_plot_style(ax4, "AVG RATE COMPARISON")
        self.embed_chart(fig4, self.frame_v_chart2)

    # --- HANDLE EDIT CLICK ---
    def on_bill_double_click(self, event):
        item = self.tree.selection()
        if not item: return
        bill_no = self.tree.item(item[0])['values'][0]
        # Switch tab and load data (function in MainApp)
        self.master.master.load_bill_for_editing(bill_no)