import customtkinter as ctk
from tkinter import ttk, messagebox, Toplevel
from tkcalendar import DateEntry
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import database
from datetime import date, timedelta

# --- Theme Colors (Matches Entry Screen) ---
THEME_COLOR = "#1f6aa5"
THEME_HOVER = "#144d7a"

class ProcessingReportsFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.df = pd.DataFrame()
        
        # --- HEADER SECTION ---
        f1 = ctk.CTkFrame(self, fg_color=("gray90", "gray13"), corner_radius=8)
        f1.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(f1, text="PROCESSING REPORTS", font=("Arial", 16, "bold"), text_color=THEME_COLOR).pack(side="left", padx=20, pady=10)
        
        # Date Filters
        ctk.CTkLabel(f1, text="FROM:", font=("Arial", 11, "bold")).pack(side="left", padx=5)
        self.start = DateEntry(f1, width=12, background=THEME_COLOR, foreground='white', borderwidth=2, date_pattern='y-mm-dd')
        self.start.set_date(date.today() - timedelta(days=30))
        self.start.pack(side="left", padx=5)
        
        ctk.CTkLabel(f1, text="TO:", font=("Arial", 11, "bold")).pack(side="left", padx=5)
        self.end = DateEntry(f1, width=12, background=THEME_COLOR, foreground='white', borderwidth=2, date_pattern='y-mm-dd')
        self.end.pack(side="left", padx=5)
        
        # Load Button
        ctk.CTkButton(f1, text="LOAD DATA", command=self.load_data, fg_color=THEME_COLOR, hover_color=THEME_HOVER, height=32, font=("Arial", 12, "bold")).pack(side="left", padx=20)

        # --- KPI CARDS ROW ---
        f2 = ctk.CTkFrame(self, fg_color="transparent")
        f2.pack(fill="x", padx=5, pady=5)
        self.k_batches = self.create_kpi_card(f2, "TOTAL BATCHES", "0")
        self.k_bags = self.create_kpi_card(f2, "TOTAL BAGS PROCESSED", "0")
        self.k_weight = self.create_kpi_card(f2, "TOTAL WEIGHT (QTL)", "0.00")

        # --- CHARTS ROW ---
        chart_container = ctk.CTkFrame(self, fg_color="transparent")
        chart_container.pack(fill="x", padx=5, pady=5)
        
        self.frame_chart1 = ctk.CTkFrame(chart_container, fg_color=("gray90", "gray13"), corner_radius=10)
        self.frame_chart1.pack(side="left", fill="both", expand=True, padx=(0,5))
        
        self.frame_chart2 = ctk.CTkFrame(chart_container, fg_color=("gray90", "gray13"), corner_radius=10)
        self.frame_chart2.pack(side="right", fill="both", expand=True, padx=(5,0))

        # --- DATA TABLE ROW ---
        f3 = ctk.CTkFrame(self, fg_color=("gray90", "gray13"), corner_radius=10)
        f3.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(f3, text="RECENT BATCHES (DOUBLE-CLICK ROW FOR DETAILS)", font=("Arial", 12, "bold"), text_color="gray").pack(anchor="w", padx=15, pady=(10,5))

        # Treeview Configuration
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#2b2b2b", foreground="white", fieldbackground="#2b2b2b", borderwidth=0, font=("Arial", 10))
        style.configure("Treeview.Heading", background=THEME_COLOR, foreground="white", font=("Arial", 11, "bold"), borderwidth=0)
        style.map("Treeview", background=[('selected', THEME_HOVER)])

        cols = ["BATCH NO", "DATE", "FIN YEAR", "TOTAL BAGS", "TOTAL WEIGHT (QTL)", "VARIETIES SUMMARY"]
        self.tree = ttk.Treeview(f3, columns=cols, show="headings", height=8)
        
        for c in cols:
            self.tree.heading(c, text=c)
            w = 400 if c == "VARIETIES SUMMARY" else 100
            self.tree.column(c, width=w, anchor="center" if c != "VARIETIES SUMMARY" else "w")
            
        scrollbar = ttk.Scrollbar(f3, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y", padx=(0, 10), pady=10)
        self.tree.pack(fill="both", expand=True, padx=(10, 0), pady=10)
        
        # Bind Double Click
        self.tree.bind("<Double-1>", self.on_double_click)

    def create_kpi_card(self, parent, title, value):
        card = ctk.CTkFrame(parent, fg_color=("gray85", "gray16"), corner_radius=10)
        card.pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkLabel(card, text=title, font=("Arial", 11, "bold"), text_color="white").pack(pady=(15,0))
        lbl = ctk.CTkLabel(card, text=value, font=("Arial", 24, "bold"), text_color="white")
        lbl.pack(pady=(0,15))
        return lbl

    def embed_chart(self, fig, parent):
        for widget in parent.winfo_children(): widget.destroy()
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    def dark_plot_style(self, ax, title):
        ax.set_facecolor("#2b2b2b")
        ax.tick_params(axis='x', colors='white', labelsize=8)
        ax.tick_params(axis='y', colors='white', labelsize=8)
        ax.spines['bottom'].set_color('white')
        ax.spines['top'].set_color('none')
        ax.spines['left'].set_color('white')
        ax.spines['right'].set_color('none')
        ax.set_title(title, color='white', pad=15, fontweight="bold", fontsize=10)

    def load_data(self):
        try:
            # 1. Fetch Main Report
            df = database.get_processing_report(self.start.get(), self.end.get())
            self.tree.delete(*self.tree.get_children())
            
            if df.empty:
                messagebox.showinfo("Info", "No processing records found for this period.")
                # Clear KPIs
                self.k_batches.configure(text="0")
                self.k_bags.configure(text="0")
                self.k_weight.configure(text="0.00")
                return

            # 2. Update KPIs
            self.k_batches.configure(text=str(len(df)))
            self.k_bags.configure(text=f"{df['total_input_bags'].sum():,.0f}")
            self.k_weight.configure(text=f"{df['total_input_weight_kg'].sum()/100:,.2f}") # KG to QTL

            # 3. Populate Table
            for _, r in df.iterrows():
                self.tree.insert("", "end", values=[
                    r['batch_no'], 
                    r['date'], 
                    r['financial_year'],
                    r['total_input_bags'],
                    f"{r['total_input_weight_kg']/100:,.2f}", # QTL
                    r['varieties']
                ])

            # 4. Chart 1: Daily Trend
            df['date'] = pd.to_datetime(df['date'])
            trend = df.groupby('date')['total_input_weight_kg'].sum() / 100 # QTL
            
            fig1 = Figure(figsize=(5, 2.5), dpi=100, facecolor="#2b2b2b")
            ax1 = fig1.add_subplot(111)
            ax1.bar(trend.index.strftime('%d-%b'), trend.values, color=THEME_COLOR, alpha=0.9)
            self.dark_plot_style(ax1, "DAILY PROCESSED WEIGHT (QTL)")
            self.embed_chart(fig1, self.frame_chart1)

            # 5. Chart 2: Variety Consumption (Pie)
            stats = database.get_processing_variety_stats(self.start.get(), self.end.get())
            fig2 = Figure(figsize=(5, 2.5), dpi=100, facecolor="#2b2b2b")
            ax2 = fig2.add_subplot(111)
            
            if not stats.empty:
                colors = ['#1f6aa5', '#ff9f1c', '#2ec4b6', '#e71d36', '#8d99ae']
                # Filter out tiny slices for cleaner look
                stats = stats[stats['total_weight'] > 0]
                
                ax2.pie(stats['total_weight'], labels=stats['paddy_type'], autopct='%1.1f%%', 
                        colors=colors, textprops={'color':"white", 'fontsize': 8}, pctdistance=0.8)
                # Donut style
                fig2.gca().add_artist(__import__('matplotlib.patches').patches.Circle((0,0),0.65,fc='#2b2b2b'))
            
            self.dark_plot_style(ax2, "CONSUMPTION BY VARIETY")
            self.embed_chart(fig2, self.frame_chart2)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load reports: {str(e)}")

    # --- DETAIL POPUP ---
    def on_double_click(self, event):
        item = self.tree.selection()
        if not item: return
        
        # Get Batch No from the first column of selected row
        batch_no = self.tree.item(item[0])['values'][0]
        
        # Fetch Detail Data
        df = database.get_batch_items_by_no(batch_no)
        if df.empty: return

        # Create Popup Window
        top = Toplevel(self)
        top.title(f"Batch {batch_no} - Full Composition")
        top.geometry("650x400")
        top.configure(bg="#2b2b2b")
        # Center the popup
        top.geometry(f"+{self.winfo_rootx() + 100}+{self.winfo_rooty() + 100}")
        
        # Popup Header
        ctk.CTkLabel(top, text=f"BATCH {batch_no} DETAILS", font=("Arial", 18, "bold"), text_color=THEME_COLOR, bg_color="#2b2b2b").pack(pady=(20, 10))
        
        # Popup Table
        cols = ["VARIETY", "BAGS PROCESSED", "AVG WEIGHT (KG)", "TOTAL WEIGHT (KG)"]
        tree = ttk.Treeview(top, columns=cols, show="headings", height=10)
        
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, anchor="center", width=140)
            
        for _, r in df.iterrows():
            tree.insert("", "end", values=[
                r['paddy_type'],
                r['bags'],
                f"{r['avg_weight_kg']:.2f}",
                f"{r['total_weight_kg']:.2f}"
            ])
            
        tree.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Close Button
        ctk.CTkButton(top, text="CLOSE", command=top.destroy, fg_color="#D32F2F", width=100).pack(pady=(0, 20))