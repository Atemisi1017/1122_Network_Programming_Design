# server

import socket
import threading
import time
import struct
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta

# 設置TCP和UDP端口
TCP_PORT = 5000
UDP_PORT = 5001
MULTICAST_GROUP = '224.1.1.1'

# 預設股票名稱
current_stock = 'AAPL'

# 獲取股票數據
def fetch_stock_data(stock_ticker):
    stock = yf.Ticker(stock_ticker)

    today = datetime.now()
    yesterday = datetime.now() - timedelta(1)
    today_str = today.strftime('%Y-%m-%d')
    yesterday_str = yesterday.strftime('%Y-%m-%d')

    # 使用 history 方法獲取歷史數據
    historical_data = stock.history(period="1d", interval="1m", start=None, end=None, actions=True, auto_adjust=True, back_adjust=False)
    data = stock.history(start=yesterday_str, end=today_str)

    if historical_data.empty or data.empty:
        raise ValueError("未能獲取歷史數據")

    close_prices = [round(price, 2) for price in historical_data['Close'].values]
    open_price = round(historical_data['Open'].iloc[0], 2)
    high_price = round(max(historical_data['High']), 2)
    low_price = round(min(historical_data['Low']), 2)
    latest_price = round(historical_data['Close'].iloc[-1], 2)
    yesterday_close = round(data['Close'].iloc[0], 2)

    return {
        'ticker': stock_ticker,
        'open': open_price,
        'high': high_price,
        'low': low_price,
        'latest': latest_price,
        'prices': close_prices,
        'yesterday': yesterday_close
    }

# 多播股票數據
def multicast_stock_data():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 32)

    while True:
        try:
            stock_data = fetch_stock_data(current_stock)
            message = str(stock_data).encode('utf-8')
            sock.sendto(message, (MULTICAST_GROUP, UDP_PORT))
            time.sleep(1)
        except Exception as e:
            print(f"Error fetching or multicasting stock data: {e}")

# 處理客戶端請求
def handle_client(client_socket, addr):
    global current_stock
    print(f"Client {addr} connected")
    try:
        while True:
            data = client_socket.recv(1024)
            if not data:
                break
            current_stock = data.decode('utf-8')
            print(f"Changed stock to: {current_stock}")
    except Exception as e:
        print(f"Error handling client {addr}: {e}")
    finally:
        client_socket.close()

# TCP服務
def tcp_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', TCP_PORT))
    server_socket.listen(5)
    print(f"TCP server listening on port {TCP_PORT}")

    while True:
        client_socket, addr = server_socket.accept()
        client_thread = threading.Thread(target=handle_client, args=(client_socket, addr), daemon=True)
        client_thread.start()

# 主程式
if __name__ == "__main__":
    threading.Thread(target=tcp_server, daemon=True).start()
    threading.Thread(target=multicast_stock_data, daemon=True).start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Server shutting down.")
