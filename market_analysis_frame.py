import customtkinter as ctk
from tkinter import ttk
import pandas as pd
import database
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import datetime

# --- WALL STREET THEME ---
BG_DARK = "#0d1117"       # Deepest Dark
BG_CARD = "#161b22"       # Card Background
ACCENT_GREEN = "#00d26a"  # Stock Up Green
ACCENT_RED = "#f85149"    # Stock Down Red
ACCENT_BLUE = "#58a6ff"   # Tech Blue
TEXT_MAIN = "white"
TEXT_SUB = "#8b949e"

class MarketAnalysisFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        
        # --- 1. LIVE TICKER (Top Bar) ---
        self.ticker_frame = ctk.CTkFrame(self, fg_color=BG_CARD, height=40, corner_radius=0)
        self.ticker_frame.pack(fill="x", side="top")
        self.ticker_lbl = ctk.CTkLabel(self.ticker_frame, text="LOADING MARKET DATA...", font=("Consolas", 12, "bold"), text_color=ACCENT_GREEN)
        self.ticker_lbl.pack(side="left", padx=20, pady=5)

        # --- 2. HEADER & CONTROLS ---
        ctrl_frame = ctk.CTkFrame(self, fg_color="transparent")
        ctrl_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        ctk.CTkLabel(ctrl_frame, text="PADDY PRICE ANALYZER", font=("Arial", 24, "bold"), text_color=ACCENT_BLUE).pack(side="left")
        
        self.refresh_btn = ctk.CTkButton(ctrl_frame, text="⟳ REFRESH MARKET", command=self.refresh_data, fg_color="#21262d", hover_color="#30363d", width=150)
        self.refresh_btn.pack(side="right")

        # --- 3. MAIN DASHBOARD GRID ---
        self.grid_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.grid_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # --- LEFT: CONTROL PANEL & SIGNALS ---
        self.side_panel = ctk.CTkFrame(self.grid_frame, fg_color=BG_CARD, width=300, corner_radius=10)
        self.side_panel.pack(side="left", fill="y", padx=(0, 15))
        self.side_panel.pack_propagate(False)
        
        # Variety Selector
        ctk.CTkLabel(self.side_panel, text="SELECT ASSET (VARIETY)", font=("Arial", 11, "bold"), text_color="gray").pack(anchor="w", padx=20, pady=(20, 5))
        self.var_menu = ctk.CTkOptionMenu(self.side_panel, values=[], fg_color=ACCENT_BLUE, button_color="#1f6feb", width=260, command=self.update_analysis)
        self.var_menu.pack(padx=20)
        
        # Big Price Display
        self.price_card = ctk.CTkFrame(self.side_panel, fg_color="#21262d", corner_radius=10)
        self.price_card.pack(fill="x", padx=20, pady=20)
        ctk.CTkLabel(self.price_card, text="LATEST TRADED PRICE", font=("Arial", 10), text_color="gray").pack(pady=(10,0))
        self.lbl_big_price = ctk.CTkLabel(self.price_card, text="₹ --", font=("Arial", 32, "bold"), text_color="white")
        self.lbl_big_price.pack(pady=(0, 10))
        
        # AI Signal Box
        self.signal_card = ctk.CTkFrame(self.side_panel, fg_color="transparent", border_width=2, border_color="gray", corner_radius=10)
        self.signal_card.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(self.signal_card, text="AI TRADE SIGNAL", font=("Arial", 12, "bold"), text_color="white").pack(pady=(10,5))
        self.lbl_signal = ctk.CTkLabel(self.signal_card, text="WAITING FOR DATA", font=("Arial", 18, "bold"), text_color="gray")
        self.lbl_signal.pack(pady=(0, 15))

        # Stats List
        self.lbl_high = self.create_stat_row(self.side_panel, "52-Week High")
        self.lbl_low = self.create_stat_row(self.side_panel, "52-Week Low")
        self.lbl_volatility = self.create_stat_row(self.side_panel, "Price Volatility")

        # --- RIGHT: THE CHART ---
        self.chart_area = ctk.CTkFrame(self.grid_frame, fg_color=BG_CARD, corner_radius=10)
        self.chart_area.pack(side="right", fill="both", expand=True)
        
        self.refresh_data()

    def create_stat_row(self, parent, title):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(fill="x", padx=25, pady=8)
        ctk.CTkLabel(f, text=title, font=("Arial", 12), text_color="gray").pack(side="left")
        lbl = ctk.CTkLabel(f, text="--", font=("Arial", 12, "bold"), text_color="white")
        lbl.pack(side="right")
        return lbl

    def refresh_data(self):
        # 1. Update Ticker
        try:
            df = database.get_latest_prices()
            if not df.empty:
                ticker_text = "  |  ".join([f"{r['paddy_type']}: ₹{r['base_rate']}" for _, r in df.iterrows()])
                self.ticker_lbl.configure(text=f"🔴 LIVE MARKET:  {ticker_text}  (Rates per Quintal)")
            
            # 2. Update Dropdown
            vars = [v[1] for v in database.get_all_paddy_varieties()]
            if vars:
                self.var_menu.configure(values=vars)
                self.var_menu.set(vars[0])
                self.update_analysis(vars[0])
        except Exception as e:
            print(f"Market Data Error: {e}")

    def update_analysis(self, variety):
        df = database.get_price_history(variety)
        if df.empty: return

        # --- 1. CALCULATE METRICS ---
        current_price = df.iloc[-1]['rate']
        all_time_high = df['rate'].max()
        all_time_low = df['rate'].min()
        avg_price = df['rate'].mean()
        
        # Volatility (Standard Deviation)
        volatility = df['rate'].std()
        vol_text = "STABLE (Safe)" if volatility < 50 else "HIGH (Risky)"
        
        # --- 2. UPDATE UI ---
        self.lbl_big_price.configure(text=f"₹ {current_price:,.0f}")
        self.lbl_high.configure(text=f"₹ {all_time_high:,.0f}")
        self.lbl_low.configure(text=f"₹ {all_time_low:,.0f}")
        self.lbl_volatility.configure(text=vol_text)

        # --- 3. AI SIGNAL LOGIC ---
        # Logic: Buy if price is near Low or below Average. Sell/Wait if near High.
        if current_price <= all_time_low * 1.05:
            self.lbl_signal.configure(text="STRONG BUY 🟢", text_color=ACCENT_GREEN)
            self.signal_card.configure(border_color=ACCENT_GREEN)
        elif current_price < avg_price:
            self.lbl_signal.configure(text="GOOD VALUE 🔵", text_color=ACCENT_BLUE)
            self.signal_card.configure(border_color=ACCENT_BLUE)
        elif current_price >= all_time_high * 0.95:
            self.lbl_signal.configure(text="OVERPRICED 🔴", text_color=ACCENT_RED)
            self.signal_card.configure(border_color=ACCENT_RED)
        else:
            self.lbl_signal.configure(text="HOLD / NEUTRAL ⚪", text_color="white")
            self.signal_card.configure(border_color="gray")

        # --- 4. PLOT CHART ---
        self.plot_chart(df, variety)

    def plot_chart(self, df, title):
        for widget in self.chart_area.winfo_children(): widget.destroy()
        
        fig = Figure(figsize=(6, 4), dpi=100, facecolor=BG_CARD)
        ax = fig.add_subplot(111)
        ax.set_facecolor(BG_CARD)
        
        df['date'] = pd.to_datetime(df['date'])
        
        # Gradient Fill Effect (Simulated with fill_between)
        ax.plot(df['date'], df['rate'], color=ACCENT_BLUE, linewidth=2)
        ax.fill_between(df['date'], df['rate'], df['rate'].min(), color=ACCENT_BLUE, alpha=0.1)
        
        # Draw Average Line
        avg = df['rate'].mean()
        ax.axhline(avg, color='gray', linestyle='--', linewidth=1, alpha=0.5, label=f"Avg: {avg:.0f}")
        
        ax.set_title(f"{title} PRICE TREND (₹/Qtl)", color="white", fontsize=10, pad=10)
        
        # Dark Theme Styling
        ax.tick_params(colors=TEXT_SUB, labelsize=8)
        ax.spines['bottom'].set_color(TEXT_SUB)
        ax.spines['left'].set_color(TEXT_SUB)
        ax.spines['top'].set_color('none')
        ax.spines['right'].set_color('none')
        ax.grid(True, color="#30363d", linestyle='--')
        
        canvas = FigureCanvasTkAgg(fig, master=self.chart_area)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)