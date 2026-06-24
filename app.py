import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Scalping IDX Harian", layout="wide", page_icon="⚡")
st.title("⚡ Scalping IDX - Mode Harian dengan Chart")
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
                current_price = last['Close']

                # Indikator
                delta = data['Close'].diff()
                gain = delta.where(delta > 0, 0).rolling(14).mean().iloc[-1]
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean().iloc[-1]
                rsi = 100 - (100 / (1 + gain/loss)) if loss != 0 else 50

                exp1 = data['Close'].ewm(span=8, adjust=False).mean()
                exp2 = data['Close'].ewm(span=17, adjust=False).mean()
                macd_line = exp1 - exp2
                macd_signal = macd_line.ewm(span=9, adjust=False).mean()
                macd_hist = macd_line - macd_signal

                data['TP'] = (data['High'] + data['Low'] + data['Close']) / 3
                data['VWAP'] = (data['TP'] * data['Volume']).cumsum() / data['Volume'].cumsum()
                vwap = data['VWAP'].iloc[-1]

                ema9 = data['Close'].ewm(span=9).mean().iloc[-1]
                ema21 = data['Close'].ewm(span=21).mean().iloc[-1]

                change_5m = round(((current_price - data.iloc[-2]['Close']) / data.iloc[-2]['Close']) * 100, 2)

                # Sinyal
                signal = "Neutral"
                score = 50
                if (current_price > vwap) and (rsi < 45) and (macd_hist.iloc[-1] > 0):
                    signal = "🟢 STRONG BUY"
                    score = 88
                elif (current_price > vwap) and (rsi < 52) and (macd_hist.iloc[-1] > 0):
                    signal = "🟢 BUY"
                    score = 72
                elif (current_price < vwap) and (rsi > 58) and (macd_hist.iloc[-1] < 0):
                    signal = "🔴 STRONG SELL"
                    score = 88
                elif (current_price < vwap) and (rsi > 52) and (macd_hist.iloc[-1] < 0):
                    signal = "🔴 SELL"
                    score = 72

                # === CHART PLOTLY ===
                fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                                    row_heights=[0.5, 0.2, 0.3], vertical_spacing=0.05)

                # Candlestick
                fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'],
                                             low=data['Low'], close=data['Close'], name="Price"), row=1, col=1)

                # EMA & VWAP
                fig.add_trace(go.Scatter(x=data.index, y=data['Close'].ewm(span=9).mean(), name="EMA 9", line=dict(color='orange')), row=1, col=1)
                fig.add_trace(go.Scatter(x=data.index, y=data['Close'].ewm(span=21).mean(), name="EMA 21", line=dict(color='blue')), row=1, col=1)
                fig.add_trace(go.Scatter(x=data.index, y=data['VWAP'], name="VWAP", line=dict(color='purple', dash='dash')), row=1, col=1)

                # Volume
                fig.add_trace(go.Bar(x=data.index, y=data['Volume'], name="Volume", marker_color='lightblue'), row=2, col=1)

                # RSI
                fig.add_trace(go.Scatter(x=data.index, y=[rsi]*len(data), name="RSI", line=dict(color='red')), row=3, col=1)
                fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
                fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)

                fig.update_layout(height=800, title_text=f"{ticker.replace('.JK','')} - Scalping 5 Menit")
                fig.update_xaxes(rangeslider_visible=False)

                # Tampilkan Info + Chart
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.metric("Harga Saat Ini", f"Rp {current_price:,.0f}", f"{change_5m}%")
                    st.write(f"**Signal:** {signal} | **Score:** {score}")
                    st.write(f"**RSI:** {round(rsi,1)} | **VWAP:** {round(vwap,2)}")
                    st.write(f"**Entry:** {current_price:.2f} | **Stop Loss:** {current_price*0.985:.2f} | **Target:** {current_price*1.022:.2f}")

                with col2:
                    st.plotly_chart(fig, use_container_width=True)

            except Exception as e:
                st.error(f"Error pada {ticker}: {str(e)}")

st.caption("Chart interaktif dengan Plotly • Refresh setiap 5-10 menit saat pasar buka • Score ≥ 75 = sinyal bagus")
