# client

import socket
import threading
import tkinter as tk
import struct
import queue
import ast
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from scipy import stats
import time

# 設置TCP和UDP端口
TCP_PORT = 5000
UDP_PORT = 5001
MULTICAST_GROUP = '224.1.1.1'

# 儲存接收到的股票數據
data_queue = queue.Queue()

# 股票市场时间段映射
market_times = {
    'TW': {'start': 9 * 60, 'end': 13 * 60 + 30},  # Taiwan Stock Exchange: 09:00 - 13:30
    'US': {'start': 9 * 60 + 30, 'end': 16 * 60},  # US Stock Market: 09:30 - 16:00
    'HK': {'start': 9 * 60 + 30, 'end': 16 * 60},  # Hong Kong Stock Exchange: 09:30 - 16:00
    'JP': {'start': 9 * 60, 'end': 15 * 60},       # Japan Stock Exchange: 09:00 - 15:00
    'CN': {'start': 9 * 60 + 30, 'end': 15 * 60},  # China Stock Exchange: 09:30 - 15:00
    'UK': {'start': 8 * 60, 'end': 16 * 60 + 30},  # London Stock Exchange: 08:00 - 16:30
    'DE': {'start': 9 * 60, 'end': 17 * 60 + 30},  # Frankfurt Stock Exchange: 09:00 - 17:30
    'AU': {'start': 10 * 60, 'end': 16 * 60},      # Australian Stock Exchange: 10:00 - 16:00
    'IN': {'start': 9 * 60 + 15, 'end': 15 * 60 + 30},  # India Stock Exchange: 09:15 - 15:30
    'CA': {'start': 9 * 60 + 30, 'end': 16 * 60},  # Toronto Stock Exchange: 09:30 - 16:00
}

# 接收多播數據
def receive_multicast():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', UDP_PORT))
    mreq = struct.pack('4sl', socket.inet_aton(MULTICAST_GROUP), socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    while True:
        message, _ = sock.recvfrom(4096)
        stock_data = ast.literal_eval(message.decode('utf-8'))
        data_queue.put(stock_data)

# 判斷股票代碼所屬市場
def determine_market(ticker):
    if '.' in ticker:
        if ticker.endswith('.TW'):
            return 'TW'
        elif ticker.endswith('.HK'):
            return 'HK'
        elif ticker.endswith('.SS') or ticker.endswith('.SZ'):
            return 'CN'
        elif ticker.endswith('.L'):
            return 'UK'
        elif ticker.endswith('.DE'):
            return 'DE'
        elif ticker.endswith('.AX'):
            return 'AU'
        elif ticker.endswith('.BO'):
            return 'IN'
        elif ticker.endswith('.TO'):
            return 'CA'
    elif ticker.isdigit():
        return 'JP'  # Japan stock codes are numeric
    else:
        return 'US'  # Default to US stock exchange

# 更新圖表
def update_chart(figure, ax, stock_data_var, latest_price_label, volume_label, open_price_label, high_price_label, low_price_label, yesterday_label, stock_name_label):
    if not data_queue.empty():
        stock_data = data_queue.get()
        stock_data_var.set(stock_data)

        ticker = stock_data['ticker']
        open_price = round(stock_data['open'], 2)
        high_price = round(stock_data['high'], 2)
        low_price = round(stock_data['low'], 2)
        latest_price = round(stock_data['latest'], 2)
        prices = [round(price, 2) for price in stock_data['prices']]
        yesterday = round(stock_data['yesterday'], 2)

        # 設置最新股價顏色
        price_diff = round(latest_price - yesterday, 2)
        if price_diff > 0:
            latest_price_label.config(fg='red')
            latest_price_text = f"最新股價: {latest_price} ↑ (+{price_diff:.2f})"
        elif price_diff < 0:
            latest_price_label.config(fg='green')
            latest_price_text = f"最新股價: {latest_price} ↓ ({price_diff:.2f})"
        else:
            latest_price_label.config(fg='black')
            latest_price_text = f"最新股價: {latest_price} - (0.0)"

        latest_price_label.config(text=latest_price_text)
        volume_label.config(text=f"成交: {latest_price}")
        open_price_label.config(text=f"開盤: {open_price}")
        high_price_label.config(text=f"最高: {high_price}")
        low_price_label.config(text=f"最低: {low_price}")
        yesterday_label.config(text=f"昨收: {yesterday}")
        stock_name_label.config(text=ticker)

        ax.clear()
        ax.plot(prices, label=ticker)
        
        # 計算趨勢線
        x = np.arange(len(prices))
        slope, intercept, _, _, _ = stats.linregress(x, prices)
        trendline = intercept + slope * x
        ax.plot(trendline, label=f"Trendline ({ticker})", linestyle='--', color='green')
        
        market = determine_market(ticker)
        
        market_time = market_times[market]
        
        market_time = market_times[market]
        total_minutes = market_time['end'] - market_time['start']
        time_labels = [f"{hour}:{minute:02d}" for hour in range(market_time['start']//60, market_time['end']//60 + 1)
                       for minute in range(0, 60, 30) if market_time['start'] <= hour * 60 + minute < market_time['end']]
        
        ax.set_xticks(np.linspace(0, total_minutes-1, len(time_labels)))
        ax.set_xticklabels(time_labels, rotation=45, ha='right')
        
        ax.legend()
        figure.canvas.draw()

    root.after(1000, update_chart, figure, ax, stock_data_var, latest_price_label, volume_label, open_price_label, high_price_label, low_price_label, yesterday_label, stock_name_label)

# GUI設計
def create_gui():
    global root, stock_entry, stock_entry_button
    root = tk.Tk()
    root.title("Stock Prices")

    stock_name_label = tk.Label(root, font=("Helvetica", 16))
    stock_name_label.pack()

    latest_price_label = tk.Label(root, font=("Helvetica", 14))
    latest_price_label.pack()

    stock_entry = tk.Entry(root)
    stock_entry.pack(pady=10)

    stock_entry_button = tk.Button(root, text="查詢", command=send_stock_request)
    stock_entry_button.pack(pady=5)

    main_frame = tk.Frame(root)
    main_frame.pack(fill=tk.BOTH, expand=True)

    figure = plt.Figure()
    ax = figure.add_subplot(111)
    canvas = FigureCanvasTkAgg(figure, main_frame)
    canvas.get_tk_widget().pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    stats_frame = tk.Frame(main_frame)
    stats_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=20, pady=20)

    volume_label = tk.Label(stats_frame, font=("Helvetica", 12))
    volume_label.pack(anchor=tk.CENTER, pady=10)

    open_price_label = tk.Label(stats_frame, font=("Helvetica", 12))
    open_price_label.pack(anchor=tk.CENTER, pady=10)

    high_price_label = tk.Label(stats_frame, font=("Helvetica", 12))
    high_price_label.pack(anchor=tk.CENTER, pady=10)

    low_price_label = tk.Label(stats_frame, font=("Helvetica", 12))
    low_price_label.pack(anchor=tk.CENTER, pady=10)

    yesterday_label = tk.Label(stats_frame, font=("Helvetica", 12))
    yesterday_label.pack(anchor=tk.CENTER, pady=10)

    stock_data_var = tk.StringVar()
    threading.Thread(target=receive_multicast, daemon=True).start()
    root.after(1000, update_chart, figure, ax, stock_data_var, latest_price_label, volume_label, open_price_label, high_price_label, low_price_label, yesterday_label, stock_name_label)

    root.mainloop()

# 發送股票詢請求
def send_stock_request():
    stock_name = stock_entry.get()
    client_socket.sendall(stock_name.encode('utf-8'))

# 訂閱股票數據
def subscribe_to_server():
    global client_socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(('localhost', TCP_PORT))
    while True:
        time.sleep(1)

# 主程式
if __name__ == "__main__":
    threading.Thread(target=subscribe_to_server, daemon=True).start()
    create_gui()
