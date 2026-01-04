import customtkinter as ctk
from tkinter import ttk
import pandas as pd
import database
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import calendar

# --- THEME ---
THEME_BG = "#1a1a1a"
ACCENT = "#8e44ad"  # Intelligence Purple
TEXT_WHITE = "white"

class BusinessIntelligenceFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        
        # --- HEADER ---
        ctk.CTkLabel(self, text="BUSINESS INTELLIGENCE & DEEP INSIGHTS", font=("Arial", 22, "bold"), text_color=ACCENT).pack(pady=(10, 20), anchor="w", padx=20)

        # --- GRID LAYOUT ---
        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure((0, 1), weight=1)

        # --- TOP ROW: INSIGHT CARDS ---
        self.top_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.top_frame.pack(fill="x", padx=10, pady=5)
        
        self.card1 = self.create_insight_card(self.top_frame, "🏆 BEST VALUE SUPPLIER", "Loading...", "Avg Rate: ₹0")
        self.card2 = self.create_insight_card(self.top_frame, "⚠️ MOISTURE ALERT", "Loading...", "Avg Moisture: 0%")
        self.card3 = self.create_insight_card(self.top_frame, "📅 PEAK BUYING MONTH", "Loading...", "Total Volume: 0")

        # --- MIDDLE ROW: CHARTS ---
        self.chart_container = ctk.CTkFrame(self, fg_color="transparent")
        self.chart_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.left_chart = ctk.CTkFrame(self.chart_container, fg_color=("gray90", "gray13"), corner_radius=10)
        self.left_chart.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        self.right_chart = ctk.CTkFrame(self.chart_container, fg_color=("gray90", "gray13"), corner_radius=10)
        self.right_chart.pack(side="right", fill="both", expand=True, padx=(5, 0))

        # --- REFRESH BUTTON ---
        ctk.CTkButton(self, text="REFRESH INSIGHTS", command=self.load_insights, fg_color=ACCENT, height=40).pack(fill="x", padx=20, pady=20)

        self.load_insights()

    def create_insight_card(self, parent, title, main_text, sub_text):
        card = ctk.CTkFrame(parent, fg_color=("gray85", "gray16"), corner_radius=15, border_width=1, border_color=ACCENT)
        card.pack(side="left", fill="x", expand=True, padx=10)
        
        ctk.CTkLabel(card, text=title, font=("Arial", 11, "bold"), text_color=ACCENT).pack(pady=(15, 5))
        lbl_main = ctk.CTkLabel(card, text=main_text, font=("Arial", 18, "bold"), text_color="white")
        lbl_main.pack(pady=0)
        lbl_sub = ctk.CTkLabel(card, text=sub_text, font=("Arial", 11), text_color="gray")
        lbl_sub.pack(pady=(0, 15))
        
        # Store references to update later
        card.lbl_main = lbl_main
        card.lbl_sub = lbl_sub
        return card

    def load_insights(self):
        # 1. Supplier Rankings
        df_rank = database.get_supplier_rankings()
        if not df_rank.empty:
            best = df_rank.iloc[0]
            self.card1.lbl_main.configure(text=best['party_name'])
            self.card1.lbl_sub.configure(text=f"Avg Rate: ₹{best['avg_rate']:.0f} (Vol: {best['vol']})")
        
        # 2. Moisture Analysis
        df_moist = database.get_moisture_insights()
        if not df_moist.empty:
            wettest = df_moist.iloc[0]
            self.card2.lbl_main.configure(text=wettest['party_name'])
            self.card2.lbl_sub.configure(text=f"Avg Moisture: {wettest['avg_moist']:.1f}% (High!)")
            self.plot_moisture_chart(df_moist)
        else:
            self.clear_chart(self.left_chart, "NO DATA")

        # 3. Seasonal Patterns
        df_season = database.get_seasonal_buying_stats()
        if not df_season.empty:
            peak = df_season.loc[df_season['total_bags'].idxmax()]
            month_name = calendar.month_name[int(peak['month'])]
            self.card3.lbl_main.configure(text=month_name.upper())
            self.card3.lbl_sub.configure(text=f"Peak Volume: {peak['total_bags']} Bags")
            self.plot_seasonal_chart(df_season)
        else:
            self.clear_chart(self.right_chart, "NO DATA")

    def plot_moisture_chart(self, df):
        self.clear_chart(self.left_chart)
        fig = Figure(figsize=(5, 3), dpi=100, facecolor="#2b2b2b")
        ax = fig.add_subplot(111)
        ax.set_facecolor("#2b2b2b")
        
        # Horizontal Bar Chart
        colors = ['#e74c3c' if x > 16 else '#f1c40f' if x > 14 else '#2ecc71' for x in df['avg_moist']]
        bars = ax.barh(df['party_name'], df['avg_moist'], color=colors)
        ax.bar_label(bars, fmt='%.1f%%', padding=3, color='white')
        
        ax.set_title("HIGHEST MOISTURE SUPPLIERS (Risk Watch)", color="white", fontsize=10, pad=10)
        ax.tick_params(colors='white', labelsize=8)
        ax.spines['bottom'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.spines['top'].set_color('none')
        ax.spines['right'].set_color('none')
        
        canvas = FigureCanvasTkAgg(fig, master=self.left_chart)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    def plot_seasonal_chart(self, df):
        self.clear_chart(self.right_chart)
        fig = Figure(figsize=(5, 3), dpi=100, facecolor="#2b2b2b")
        ax1 = fig.add_subplot(111)
        ax1.set_facecolor("#2b2b2b")
        
        # Dual Axis: Bars for Volume, Line for Rate
        months = [calendar.month_abbr[int(m)] for m in df['month']]
        
        ax1.bar(months, df['total_bags'], color=ACCENT, alpha=0.6, label="Volume")
        ax1.set_ylabel("Bags", color=ACCENT)
        ax1.tick_params(axis='y', labelcolor=ACCENT, colors='white')
        ax1.tick_params(axis='x', colors='white')
        
        ax2 = ax1.twinx()
        ax2.plot(months, df['avg_rate'], color="#2ecc71", marker='o', linewidth=2, label="Rate")
        ax2.set_ylabel("Avg Rate (₹)", color="#2ecc71")
        ax2.tick_params(axis='y', labelcolor="#2ecc71", colors='white')
        
        ax1.set_title("SEASONAL BUYING TRENDS (Vol vs Rate)", color="white", fontsize=10, pad=10)
        ax1.spines['top'].set_color('none')
        
        canvas = FigureCanvasTkAgg(fig, master=self.right_chart)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    def clear_chart(self, parent, msg=""):
        for widget in parent.winfo_children(): widget.destroy()
        if msg: ctk.CTkLabel(parent, text=msg, text_color="gray").pack(expand=True)