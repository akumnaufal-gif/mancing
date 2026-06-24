import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Scalping IDX Harian", layout="wide", page_icon="⚡")
st.title("⚡ Scalping IDX - Mode Harian")
st.markdown("**Data 5 menit + Chart Interaktif**")

st.sidebar.header("Pengaturan")
tickers_input = st.text_area("Masukkan Ticker (pisah koma)", 
    "BBCA, BBRI, BREN, DEWA, BUVA", height=80)

if st.button("🚀 Scan Scalping Sekarang", type="primary", use_container_width=True):
    with st.spinner("Mengambil data 5 menit..."):
        tickers = [t.strip().upper() + ".JK" for t in tickers_input.split(",") if t.strip()]
        
        for ticker in tickers:
            try:
                data = yf.download(ticker, period="3d", interval="5m", progress=False)
                if len(data) < 50: 
                    st.warning(f"Data {ticker} kurang")
                    continue

                last = data.iloc[-1]
                current_price = float(last['Close'])

                # RSI
                delta = data['Close'].diff()
                gain = delta.where(delta > 0, 0).rolling(14).mean().iloc[-1]
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean().iloc[-1]
                rsi = 100 - (100 / (1 + gain/loss)) if loss != 0 else 50

                # MACD
                exp1 = data['Close'].ewm(span=8, adjust=False).mean()
                exp2 = data['Close'].ewm(span=17, adjust=False).mean()
                macd_line = exp1 - exp2
                macd_signal = macd_line.ewm(span=9, adjust=False).mean()
                macd_hist = macd_line - macd_signal

                # VWAP
                data['TP'] = (data['High'] + data['Low'] + data['Close']) / 3
                data['VWAP'] = (data['TP'] * data['Volume']).cumsum() / data['Volume'].cumsum()
                vwap = float(data['VWAP'].iloc[-1])

                ema9 = float(data['Close'].ewm(span=9).mean().iloc[-1])
                ema21 = float(data['Close'].ewm(span=21).mean().iloc[-1])

                change_5m = round(((current_price - float(data.iloc[-2]['Close'])) / float(data.iloc[-2]['Close'])) * 100, 2)

                # === SINYAL SCALPING (SUDAH DIPERBAIKI) ===
                signal = "Neutral"
                score = 50

                macd_value = float(macd_hist.iloc[-1])

                if (current_price > vwap) and (rsi < 45) and (macd_value > 0):
                    signal = "🟢 STRONG BUY"
                    score = 88
                elif (current_price > vwap) and (rsi < 52) and (macd_value > 0):
                    signal = "🟢 BUY"
                    score = 72
                elif (current_price < vwap) and (rsi > 58) and (macd_value < 0):
                    signal = "🔴 STRONG SELL"
                    score = 88
                elif (current_price < vwap) and (rsi > 52) and (macd_value < 0):
                    signal = "🔴 SELL"
                    score = 72

                # Entry & Risk
                if "BUY" in signal:
                    entry = round(current_price, 2)
                    stop_loss = round(current_price * 0.985, 2)
                    target = round(current_price * 1.022, 2)
                elif "SELL" in signal:
                    entry = round(current_price, 2)
                    stop_loss = round(current_price * 1.015, 2)
                    target = round(current_price * 0.978, 2)
                else:
                    entry = round(current_price, 2)
                    stop_loss = round(current_price * 0.99, 2)
                    target = round(current_price * 1.015, 2)

                rr = round(abs(target - entry) / abs(entry - stop_loss), 2) if (entry - stop_loss) != 0 else 0

                # === TAMPILKAN ===
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.metric(f"{ticker.replace('.JK','')}", f"Rp {current_price:,.0f}", f"{change_5m}%")
                    st.success(f"**Signal:** {signal} | **Score:** {score}")
                    st.write(f"RSI: {round(rsi,1)} | VWAP: {round(vwap,2)}")
                    st.write(f"Entry: {entry} | SL: {stop_loss} | Target: {target} | R:R {rr}")

                with col2:
                    # Chart sederhana
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=data.index, y=data['Close'], name="Price", line=dict(color="blue")))
                    fig.add_trace(go.Scatter(x=data.index, y=data['VWAP'], name="VWAP", line=dict(color="purple", dash="dash")))
                    fig.update_layout(title=f"{ticker} - 5 Menit Chart", height=400)
                    st.plotly_chart(fig, use_container_width=True)

            except Exception as e:
                st.error(f"Error pada {ticker}: {str(e)}")

st.caption("Refresh setiap 5-10 menit saat pasar buka • Score ≥ 75 = sinyal kuat")
