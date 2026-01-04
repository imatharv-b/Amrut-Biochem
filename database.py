import sqlite3
import pandas as pd
from datetime import datetime

DATABASE_FILE = "rice_mill.db"

# ======================================================================================
# CORE DATABASE SETUP & HELPER FUNCTIONS
# ======================================================================================

def execute_query(query, params=(), fetch=None):
    """Executes a SQL query safely."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute(query, params)
        
        if fetch == "one":
            result = cursor.fetchone()
        elif fetch == "all":
            result = cursor.fetchall()
        else:
            conn.commit()
            result = cursor.lastrowid
        return result
    except sqlite3.Error as e:
        print(f"DB Error: {e}")
        return None if fetch else f"DB Error: {e}"
    finally:
        if conn:
            conn.close()

def setup_database():
    """Creates all necessary tables if they don't exist."""
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    
    # 1. Master Tables
    c.execute("""CREATE TABLE IF NOT EXISTS parties (
        party_id INTEGER PRIMARY KEY, party_name TEXT NOT NULL UNIQUE, 
        gst_no TEXT, mobile_no TEXT, address TEXT);""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS paddy_varieties (
        variety_id INTEGER PRIMARY KEY, variety_name TEXT NOT NULL UNIQUE, 
        default_brokerage_rate REAL DEFAULT 0);""")
    
    # 2. Purchase Bills
    c.execute("""CREATE TABLE IF NOT EXISTS bills (
        bill_no INTEGER PRIMARY KEY, party_id INTEGER NOT NULL, bill_date TEXT NOT NULL, 
        lorry_no TEXT, total_bags INTEGER, truck_weight1_kg REAL, truck_weight2_kg REAL, 
        truck_weight3_kg REAL, final_truck_weight_kg REAL NOT NULL, 
        total_gross_amount REAL NOT NULL, discount_percent REAL DEFAULT 0, 
        brokerage REAL DEFAULT 0, hamali REAL DEFAULT 0, others_desc TEXT, 
        others_amount REAL DEFAULT 0, net_payable REAL NOT NULL, avg_pack_size_kg REAL, 
        FOREIGN KEY (party_id) REFERENCES parties (party_id));""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS bill_items (
        item_id INTEGER PRIMARY KEY, bill_no INTEGER NOT NULL, paddy_type TEXT NOT NULL, 
        bags INTEGER NOT NULL, moisture REAL, base_rate REAL NOT NULL, 
        calculated_rate REAL NOT NULL, calculated_weight_kg REAL NOT NULL, 
        item_amount REAL NOT NULL, FOREIGN KEY (bill_no) REFERENCES bills (bill_no));""")
    
    # 3. Sales Bills
    c.execute("""CREATE TABLE IF NOT EXISTS sales_bills (
        bill_no INTEGER PRIMARY KEY, party_id INTEGER NOT NULL, bill_date TEXT NOT NULL, 
        lorry_no TEXT, total_bags INTEGER, final_weight_kg REAL NOT NULL, 
        total_gross_amount REAL NOT NULL, discount_percent REAL DEFAULT 0, 
        brokerage REAL DEFAULT 0, hamali REAL DEFAULT 0, others_desc TEXT, 
        others_amount REAL DEFAULT 0, net_payable REAL NOT NULL, 
        FOREIGN KEY (party_id) REFERENCES parties (party_id));""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS sales_bill_items (
        item_id INTEGER PRIMARY KEY, bill_no INTEGER NOT NULL, paddy_type TEXT NOT NULL, 
        bags INTEGER NOT NULL, rate REAL NOT NULL, weight_kg REAL NOT NULL, 
        amount REAL NOT NULL, FOREIGN KEY (bill_no) REFERENCES sales_bills (bill_no));""")
    
    # 4. Inventory & Processing
    c.execute("""CREATE TABLE IF NOT EXISTS inventory_log (
        log_id INTEGER PRIMARY KEY, date TEXT NOT NULL, type TEXT NOT NULL, 
        ref_id INTEGER, paddy_type TEXT NOT NULL, bags_change INTEGER NOT NULL, 
        weight_change_kg REAL NOT NULL);""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS processing_batches (
        batch_id INTEGER PRIMARY KEY, batch_no TEXT NOT NULL, date TEXT NOT NULL, 
        financial_year TEXT NOT NULL, total_input_bags INTEGER NOT NULL, 
        total_input_weight_kg REAL NOT NULL, status TEXT DEFAULT 'COMPLETED');""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS processing_batch_items (
        item_id INTEGER PRIMARY KEY, batch_id INTEGER NOT NULL, paddy_type TEXT NOT NULL, 
        bags INTEGER NOT NULL, avg_weight_kg REAL NOT NULL, total_weight_kg REAL NOT NULL, 
        FOREIGN KEY (batch_id) REFERENCES processing_batches (batch_id));""")

    conn.commit()
    conn.close()
    rebuild_inventory_from_bills()

def rebuild_inventory_from_bills():
    """Wipes inventory log and recalculates everything to fix sync issues."""
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM inventory_log")
    
    # 1. Purchase (+)
    purchases = pd.read_sql("SELECT b.bill_date, b.bill_no, i.paddy_type, i.bags, i.calculated_weight_kg FROM bills b JOIN bill_items i ON b.bill_no = i.bill_no", conn)
    for _, r in purchases.iterrows():
        c.execute("INSERT INTO inventory_log (date, type, ref_id, paddy_type, bags_change, weight_change_kg) VALUES (?, 'PURCHASE', ?, ?, ?, ?)", 
                  (r['bill_date'], r['bill_no'], r['paddy_type'], r['bags'], r['calculated_weight_kg'] * 100))
    
    # 2. Sales (-)
    try:
        sales = pd.read_sql("SELECT b.bill_date, b.bill_no, i.paddy_type, i.bags, i.weight_kg FROM sales_bills b JOIN sales_bill_items i ON b.bill_no = i.bill_no", conn)
        for _, r in sales.iterrows():
            c.execute("INSERT INTO inventory_log (date, type, ref_id, paddy_type, bags_change, weight_change_kg) VALUES (?, 'SALE', ?, ?, ?, ?)", 
                      (r['bill_date'], r['bill_no'], r['paddy_type'], -r['bags'], -(r['weight_kg'] * 100)))
    except: pass

    # 3. Processing (-)
    try:
        proc = pd.read_sql("SELECT b.date, b.batch_id, i.paddy_type, i.bags, i.total_weight_kg FROM processing_batches b JOIN processing_batch_items i ON b.batch_id = i.batch_id", conn)
        for _, r in proc.iterrows():
             c.execute("INSERT INTO inventory_log (date, type, ref_id, paddy_type, bags_change, weight_change_kg) VALUES (?, 'PROCESS_IN', ?, ?, ?, ?)", 
                       (r['date'], r['batch_id'], r['paddy_type'], -r['bags'], -r['total_weight_kg']))
    except: pass
    
    conn.commit()
    conn.close()

# ======================================================================================
# MASTER FUNCTIONS
# ======================================================================================

def add_party(name, gst, mobile, address):
    return execute_query("INSERT INTO parties (party_name, gst_no, mobile_no, address) VALUES (?,?,?,?)", (name, gst, mobile, address))
def update_party(pid, name, gst, mobile, address):
    return execute_query("UPDATE parties SET party_name=?, gst_no=?, mobile_no=?, address=? WHERE party_id=?", (name, gst, mobile, address, pid))
def delete_party(pid): return execute_query("DELETE FROM parties WHERE party_id=?", (pid,))
def get_all_parties(): return execute_query("SELECT * FROM parties ORDER BY party_name", fetch="all")
def get_party_details(pid): return execute_query("SELECT * FROM parties WHERE party_id=?", (pid,), fetch="one")
def add_paddy_variety(name, rate): return execute_query("INSERT INTO paddy_varieties (variety_name, default_brokerage_rate) VALUES (?,?)", (name, rate))
def update_paddy_variety(vid, name, rate): return execute_query("UPDATE paddy_varieties SET variety_name=?, default_brokerage_rate=? WHERE variety_id=?", (name, rate, vid))
def get_all_paddy_varieties(): return execute_query("SELECT * FROM paddy_varieties ORDER BY variety_name", fetch="all")

# ======================================================================================
# BILLING & TRANSACTION FUNCTIONS (STOCK VALIDATION ADDED)
# ======================================================================================

def get_next_bill_number(): 
    res = execute_query("SELECT MAX(bill_no) FROM bills", fetch="one")
    return (res[0] or 0) + 1 if res else 1
def get_next_sales_bill_number(): 
    res = execute_query("SELECT MAX(bill_no) FROM sales_bills", fetch="one")
    return (res[0] or 0) + 1 if res else 1

def get_paddy_avg_weight(paddy_type):
    """Returns (Total Bags, Total Weight KG, Avg Weight KG) for checking stock."""
    conn = sqlite3.connect(DATABASE_FILE)
    res = conn.execute("SELECT SUM(bags_change), SUM(weight_change_kg) FROM inventory_log WHERE paddy_type = ?", (paddy_type,)).fetchone()
    conn.close()
    bags = res[0] or 0; weight = res[1] or 0
    if bags > 0: return bags, weight, weight / bags
    return 0, 0, 0

def add_bill(header, items):
    """Saves Purchase Bill (+)"""
    conn = sqlite3.connect(DATABASE_FILE)
    try:
        cursor = conn.cursor(); cursor.execute("BEGIN TRANSACTION")
        cursor.execute("SELECT party_id FROM parties WHERE party_name = ?", (header['party_name'],))
        row = cursor.fetchone()
        party_id = row[0] if row else execute_query("INSERT INTO parties (party_name) VALUES (?)", (header['party_name'],))
        
        cursor.execute("""INSERT INTO bills (bill_no, party_id, bill_date, lorry_no, total_bags, truck_weight1_kg, truck_weight2_kg, truck_weight3_kg, final_truck_weight_kg, total_gross_amount, discount_percent, brokerage, hamali, others_desc, others_amount, net_payable, avg_pack_size_kg) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                       (header['bill_no'], party_id, header['date'], header['lorry_no'], header['total_bags'], header['truck_weight1_kg'], header['truck_weight2_kg'], header['truck_weight3_kg'], header['final_truck_weight_kg'], header['total_gross_amount'], header['discount_percent'], header['brokerage'], header['hamali'], header['others_desc'], header['others_amount'], header['net_payable'], 0))

        for i in items:
            cursor.execute("""INSERT INTO bill_items (bill_no, paddy_type, bags, moisture, base_rate, calculated_rate, calculated_weight_kg, item_amount) VALUES (?,?,?,?,?,?,?,?)""", 
                           (header['bill_no'], i['paddy_type'], i['bags'], i['moisture'], i['base_rate'], i['calculated_rate'], i['calculated_weight_kg'], i['item_amount']))
            cursor.execute("INSERT INTO inventory_log (date, type, ref_id, paddy_type, bags_change, weight_change_kg) VALUES (?, 'PURCHASE', ?, ?, ?, ?)", 
                           (header['date'], header['bill_no'], i['paddy_type'], i['bags'], i['calculated_weight_kg'] * 100))
        conn.commit(); return header['bill_no']
    except Exception as e: conn.rollback(); return f"Error: {e}"
    finally: conn.close()

def add_sales_bill(header, items):
    """Saves Sales Bill (-) with STOCK CHECK"""
    # 1. Validate Stock First
    for i in items:
        curr_bags, _, _ = get_paddy_avg_weight(i['paddy_type'])
        if curr_bags < i['bags']:
            return f"Error: Insufficient stock for {i['paddy_type']}.\nAvailable: {curr_bags} Bags\nRequired: {i['bags']} Bags"

    # 2. Proceed if Valid
    conn = sqlite3.connect(DATABASE_FILE)
    try:
        cursor = conn.cursor(); cursor.execute("BEGIN TRANSACTION")
        cursor.execute("SELECT party_id FROM parties WHERE party_name = ?", (header['party_name'],))
        row = cursor.fetchone()
        party_id = row[0] if row else execute_query("INSERT INTO parties (party_name) VALUES (?)", (header['party_name'],))
        
        cursor.execute("""INSERT INTO sales_bills (bill_no, party_id, bill_date, lorry_no, total_bags, final_weight_kg, total_gross_amount, discount_percent, brokerage, hamali, others_desc, others_amount, net_payable) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                       (header['bill_no'], party_id, header['date'], header['lorry_no'], header['total_bags'], header['final_weight_kg'], header['total_gross_amount'], header['discount_percent'], header['brokerage'], header['hamali'], header['others_desc'], header['others_amount'], header['net_payable']))

        for i in items:
            cursor.execute("""INSERT INTO sales_bill_items (bill_no, paddy_type, bags, rate, weight_kg, amount) VALUES (?,?,?,?,?,?)""", 
                           (header['bill_no'], i['paddy_type'], i['bags'], i['rate'], i['calculated_weight_kg'], i['item_amount']))
            cursor.execute("INSERT INTO inventory_log (date, type, ref_id, paddy_type, bags_change, weight_change_kg) VALUES (?, 'SALE', ?, ?, ?, ?)", 
                           (header['date'], header['bill_no'], i['paddy_type'], -i['bags'], -(i['calculated_weight_kg'] * 100)))
        conn.commit(); return header['bill_no']
    except Exception as e: conn.rollback(); return f"Error: {e}"
    finally: conn.close()

def update_bill(original_bill_no, header, items):
    conn = sqlite3.connect(DATABASE_FILE)
    try:
        cursor = conn.cursor(); cursor.execute("BEGIN TRANSACTION")
        cursor.execute("SELECT party_id FROM parties WHERE party_name = ?", (header['party_name'],))
        row = cursor.fetchone()
        party_id = row[0] if row else execute_query("INSERT INTO parties (party_name) VALUES (?)", (header['party_name'],))
        
        cursor.execute("""UPDATE bills SET party_id=?, bill_date=?, lorry_no=?, total_bags=?, truck_weight1_kg=?, truck_weight2_kg=?, truck_weight3_kg=?, final_truck_weight_kg=?, total_gross_amount=?, discount_percent=?, brokerage=?, hamali=?, others_desc=?, others_amount=?, net_payable=?, avg_pack_size_kg=? WHERE bill_no=?""", 
            (party_id, header['date'], header['lorry_no'], header['total_bags'], header['truck_weight1_kg'], header['truck_weight2_kg'], header['truck_weight3_kg'], header['final_truck_weight_kg'], header['total_gross_amount'], header['discount_percent'], header['brokerage'], header['hamali'], header['others_desc'], header['others_amount'], header['net_payable'], 0, original_bill_no))

        cursor.execute("DELETE FROM bill_items WHERE bill_no=?", (original_bill_no,))
        cursor.execute("DELETE FROM inventory_log WHERE type='PURCHASE' AND ref_id=?", (original_bill_no,))

        for i in items:
            cursor.execute("""INSERT INTO bill_items (bill_no, paddy_type, bags, moisture, base_rate, calculated_rate, calculated_weight_kg, item_amount) VALUES (?,?,?,?,?,?,?,?)""", 
                (original_bill_no, i['paddy_type'], i['bags'], i['moisture'], i['base_rate'], i['calculated_rate'], i['calculated_weight_kg'], i['item_amount']))
            cursor.execute("INSERT INTO inventory_log (date, type, ref_id, paddy_type, bags_change, weight_change_kg) VALUES (?, 'PURCHASE', ?, ?, ?, ?)", 
                (header['date'], original_bill_no, i['paddy_type'], i['bags'], i['calculated_weight_kg'] * 100))
        conn.commit(); return original_bill_no
    except Exception as e: conn.rollback(); return f"Error: {e}"
    finally: conn.close()

# ======================================================================================
# PROCESSING & REPORTING
# ======================================================================================

def get_financial_year(date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{dt.year}-{dt.year + 1}" if dt.month >= 4 else f"{dt.year - 1}-{dt.year}"

def get_next_batch_number(date_str):
    fy = get_financial_year(date_str)
    # UNLIMITED BATCHES PER DAY (Check Removed)
    
    conn = sqlite3.connect(DATABASE_FILE); cursor = conn.cursor()
    cursor.execute("SELECT batch_no FROM processing_batches WHERE financial_year = ?", (fy,)); rows = cursor.fetchall(); conn.close()
    max_num = 0
    for r in rows:
        try: num = int(r[0].split('/')[0]); max_num = max(max_num, num)
        except: pass
    short_fy = fy[2:4] + "-" + fy[7:9]; return f"{max_num + 1}/{short_fy}", None

def add_processing_batch(date_str, items_list):
    """Saves Batch with STOCK CHECK"""
    batch_no, error = get_next_batch_number(date_str)
    if error: return error
    
    total_batch_bags, total_batch_weight, processed_items = 0, 0, []

    # 1. Check Stock
    for i in items_list:
        p_type = i['paddy_type']; bags = i['bags']
        curr_bags, curr_wt, avg_wt = get_paddy_avg_weight(p_type)
        if curr_bags < bags: return f"Error: Insufficient stock for {p_type}.\nAvailable: {curr_bags} Bags\nRequired: {bags} Bags"
        if avg_wt <= 0: return f"Error: Invalid weight data for {p_type}. Check Inventory."
        item_weight = bags * avg_wt
        total_batch_bags += bags; total_batch_weight += item_weight
        processed_items.append({'paddy_type': p_type, 'bags': bags, 'avg_wt': avg_wt, 'total_wt': item_weight})

    fy = get_financial_year(date_str)
    conn = sqlite3.connect(DATABASE_FILE)
    try:
        cursor = conn.cursor(); cursor.execute("BEGIN TRANSACTION")
        cursor.execute("INSERT INTO processing_batches (batch_no, date, financial_year, total_input_bags, total_input_weight_kg) VALUES (?, ?, ?, ?, ?)", (batch_no, date_str, fy, total_batch_bags, total_batch_weight))
        batch_id = cursor.lastrowid
        for item in processed_items:
            cursor.execute("INSERT INTO processing_batch_items (batch_id, paddy_type, bags, avg_weight_kg, total_weight_kg) VALUES (?, ?, ?, ?, ?)", (batch_id, item['paddy_type'], item['bags'], item['avg_wt'], item['total_wt']))
            cursor.execute("INSERT INTO inventory_log (date, type, ref_id, paddy_type, bags_change, weight_change_kg) VALUES (?, 'PROCESS_IN', ?, ?, ?, ?)", (date_str, batch_id, item['paddy_type'], -item['bags'], -item['total_wt']))
        conn.commit(); return f"Batch {batch_no} Started Successfully!"
    except Exception as e: conn.rollback(); return f"Error: {e}"
    finally: conn.close()

def get_report_data_with_items(start, end):
    conn = sqlite3.connect(DATABASE_FILE)
    query = "SELECT b.bill_no, b.bill_date, p.party_name, b.total_bags, b.final_truck_weight_kg, b.net_payable, b.brokerage as bill_total_brokerage, i.paddy_type, i.calculated_weight_kg as item_weight, i.moisture, i.base_rate, pv.default_brokerage_rate FROM bills b JOIN parties p ON b.party_id = p.party_id JOIN bill_items i ON b.bill_no = i.bill_no LEFT JOIN paddy_varieties pv ON i.paddy_type = pv.variety_name WHERE b.bill_date BETWEEN ? AND ?"
    df = pd.read_sql_query(query, conn, params=(start, end)); conn.close(); return df

def get_inventory_summary():
    conn = sqlite3.connect(DATABASE_FILE)
    query = "SELECT paddy_type, SUM(CASE WHEN type='PURCHASE' THEN weight_change_kg ELSE 0 END) as total_in_kg, SUM(CASE WHEN type IN ('SALE', 'PROCESS_IN') THEN ABS(weight_change_kg) ELSE 0 END) as total_out_kg, SUM(weight_change_kg) as current_stock_kg, SUM(bags_change) as current_bags FROM inventory_log GROUP BY paddy_type"
    df = pd.read_sql_query(query, conn)
    rate_query = "SELECT i.paddy_type, SUM(i.item_amount) / SUM(i.calculated_weight_kg) as avg_rate FROM bill_items i GROUP BY i.paddy_type"
    df_rates = pd.read_sql_query(rate_query, conn)
    if not df.empty and not df_rates.empty:
        df = df.merge(df_rates, on="paddy_type", how="left"); df['avg_rate'] = df['avg_rate'].fillna(0); df['stock_value'] = ((df['current_stock_kg'] / 100) * df['avg_rate']).astype(int)
    else: df['avg_rate'] = 0; df['stock_value'] = 0
    conn.close(); return df

def get_inventory_ledger(paddy_type=None):
    conn = sqlite3.connect(DATABASE_FILE)
    base_query = "SELECT date, type, ref_id, paddy_type, bags_change, weight_change_kg FROM inventory_log"
    if paddy_type and paddy_type != "ALL": base_query += f" WHERE paddy_type = '{paddy_type}'"
    base_query += " ORDER BY date DESC"
    df = pd.read_sql_query(base_query, conn); conn.close(); return df

def get_processing_report(start, end):
    conn = sqlite3.connect(DATABASE_FILE)
    query = "SELECT b.batch_no, b.date, b.financial_year, b.total_input_bags, b.total_input_weight_kg, GROUP_CONCAT(i.paddy_type || ': ' || i.bags, ' | ') as varieties FROM processing_batches b LEFT JOIN processing_batch_items i ON b.batch_id = i.batch_id WHERE b.date BETWEEN ? AND ? GROUP BY b.batch_id ORDER BY b.date DESC"
    df = pd.read_sql_query(query, conn, params=(start, end)); conn.close(); return df

def get_processing_variety_stats(start, end):
    conn = sqlite3.connect(DATABASE_FILE)
    query = "SELECT i.paddy_type, SUM(i.bags) as total_bags, SUM(i.total_weight_kg) as total_weight FROM processing_batch_items i JOIN processing_batches b ON i.batch_id = b.batch_id WHERE b.date BETWEEN ? AND ? GROUP BY i.paddy_type"
    df = pd.read_sql_query(query, conn, params=(start, end)); conn.close(); return df

def get_batch_items_by_no(batch_no):
    conn = sqlite3.connect(DATABASE_FILE)
    query = "SELECT i.paddy_type, i.bags, i.avg_weight_kg, i.total_weight_kg FROM processing_batch_items i JOIN processing_batches b ON i.batch_id = b.batch_id WHERE b.batch_no = ?"
    df = pd.read_sql_query(query, conn, params=(batch_no,)); conn.close(); return df

def get_bill_details(bill_no):
    conn = sqlite3.connect(DATABASE_FILE); conn.row_factory = sqlite3.Row; cursor = conn.cursor()
    header = cursor.execute("SELECT b.*, p.party_name, p.gst_no, p.mobile_no, p.address FROM bills b JOIN parties p ON b.party_id = p.party_id WHERE b.bill_no = ?", (bill_no,)).fetchone()
    if not header: return None
    items = cursor.execute("SELECT * FROM bill_items WHERE bill_no = ?", (bill_no,)).fetchall()
    conn.close(); return {"header": dict(header), "items": [dict(i) for i in items]}

def get_sales_bill_details(bill_no):
    conn = sqlite3.connect(DATABASE_FILE); conn.row_factory = sqlite3.Row; cursor = conn.cursor()
    header = cursor.execute("SELECT b.*, p.party_name, p.gst_no, p.mobile_no, p.address FROM sales_bills b JOIN parties p ON b.party_id = p.party_id WHERE b.bill_no = ?", (bill_no,)).fetchone()
    if not header: return None
    items = cursor.execute("SELECT * FROM sales_bill_items WHERE bill_no = ?", (bill_no,)).fetchall()
    conn.close(); return {"header": dict(header), "items": [dict(i) for i in items]}
# ... (Add this to the very bottom of database.py)

def get_price_history(paddy_type):
    """Fetches historical purchase rates for a specific variety."""
    conn = sqlite3.connect(DATABASE_FILE)
    query = """
        SELECT b.bill_date as date, i.base_rate as rate
        FROM bill_items i
        JOIN bills b ON i.bill_no = b.bill_no
        WHERE i.paddy_type = ?
        ORDER BY b.bill_date ASC
    """
    df = pd.read_sql_query(query, conn, params=(paddy_type,))
    conn.close()
    return df
# ... (Add to the bottom of database.py) ...

def get_moisture_insights():
    """Finds which suppliers bring the highest moisture paddy on average."""
    conn = sqlite3.connect(DATABASE_FILE)
    query = """
        SELECT p.party_name, AVG(i.moisture) as avg_moist, SUM(i.bags) as total_bags
        FROM bill_items i
        JOIN bills b ON i.bill_no = b.bill_no
        JOIN parties p ON b.party_id = p.party_id
        GROUP BY p.party_name
        HAVING total_bags > 0
        ORDER BY avg_moist DESC
        LIMIT 5
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_seasonal_buying_stats():
    """Analyzes which months you buy the most paddy."""
    conn = sqlite3.connect(DATABASE_FILE)
    query = """
        SELECT strftime('%m', b.bill_date) as month, SUM(b.total_bags) as total_bags, AVG(i.base_rate) as avg_rate
        FROM bills b
        JOIN bill_items i ON b.bill_no = i.bill_no
        GROUP BY month
        ORDER BY month ASC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_supplier_rankings():
    """Ranks suppliers by who gives the Cheapest Rate (Best Value)."""
    conn = sqlite3.connect(DATABASE_FILE)
    query = """
        SELECT p.party_name, AVG(i.base_rate) as avg_rate, SUM(i.bags) as vol
        FROM bill_items i
        JOIN bills b ON i.bill_no = b.bill_no
        JOIN parties p ON b.party_id = p.party_id
        GROUP BY p.party_name
        ORDER BY avg_rate ASC
        LIMIT 10
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df
# --- ADD THESE TO THE BOTTOM OF database.py ---

def get_price_history(paddy_type):
    """Fetches historical purchase rates for a specific variety to build the graph."""
    conn = sqlite3.connect(DATABASE_FILE)
    query = """
        SELECT b.bill_date as date, i.base_rate as rate
        FROM bill_items i
        JOIN bills b ON i.bill_no = b.bill_no
        WHERE i.paddy_type = ?
        ORDER BY b.bill_date ASC
    """
    df = pd.read_sql_query(query, conn, params=(paddy_type,))
    conn.close()
    return df

def get_latest_prices():
    """Fetches the most recent purchase price for EVERY variety (for the ticker)."""
    conn = sqlite3.connect(DATABASE_FILE)
    query = """
        SELECT i.paddy_type, i.base_rate
        FROM bill_items i
        JOIN bills b ON i.bill_no = b.bill_no
        GROUP BY i.paddy_type
        ORDER BY b.bill_date DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df