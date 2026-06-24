import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Scalping IDX", layout="wide", page_icon="⚡")
st.title("⚡ Scalping IDX Harian")
st.markdown("**Data 5 menit - Siap dipakai saat pasar buka**")

st.sidebar.header("Pengaturan")
tickers_input = st.text_area("Ticker (pisah koma)", 
    "BBCA, BBRI, BREN, DEWA, BUVA, TLKM, ASII", height=80)

if st.button("🚀 Scan Scalping Sekarang", type="primary", use_container_width=True):
    with st.spinner("Mengambil data..."):
        tickers = [t.strip().upper() + ".JK" for t in tickers_input.split(",") if t.strip()]
        
        for ticker in tickers:
            try:
                # Ambil data
                data = yf.download(ticker, period="3d", interval="5m", progress=False)
                if len(data) < 30:
                    st.warning(f"Data {ticker} belum cukup")
                    continue

                # Ambil nilai terakhir dengan aman
                current_price = float(data['Close'].iloc[-1])
                prev_price = float(data['Close'].iloc[-2])
                change_5m = round(((current_price - prev_price) / prev_price) * 100, 2)

                # RSI
                delta = data['Close'].diff()
                gain = delta.where(delta > 0, 0).rolling(14).mean().iloc[-1]
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean().iloc[-1]
                rsi = float(100 - (100 / (1 + gain / loss))) if loss != 0 else 50.0

                # MACD sederhana
                ema_fast = data['Close'].ewm(span=8).mean()
                ema_slow = data['Close'].ewm(span=17).mean()
                macd_line = ema_fast - ema_slow
                macd_signal = macd_line.ewm(span=9).mean()
                macd_hist = float(macd_line.iloc[-1] - macd_signal.iloc[-1])

                # VWAP
                typical_price = (data['High'] + data['Low'] + data['Close']) / 3
                vwap = float((typical_price * data['Volume']).cumsum().iloc[-1] / data['Volume'].cumsum().iloc[-1])

                # Sinyal Scalping
                if rsi < 40 and current_price > vwap and macd_hist > 0:
                    signal = "🟢 STRONG BUY"
                    score = 85
                elif rsi < 48 and current_price > vwap and macd_hist > 0:
                    signal = "🟢 BUY"
                    score = 70
                elif rsi > 62 and current_price < vwap and macd_hist < 0:
                    signal = "🔴 STRONG SELL"
                    score = 85
                elif rsi > 55 and current_price < vwap and macd_hist < 0:
                    signal = "🔴 SELL"
                    score = 70
                else:
                    signal = "Neutral"
                    score = 50

                # Entry, SL, Target
                entry = round(current_price, 2)
                stop_loss = round(current_price * 0.985, 2)
                target = round(current_price * 1.022, 2)
                rr = round((target - entry) / (entry - stop_loss), 2)

                # Tampilan
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.metric(f"{ticker.replace('.JK','')}", f"Rp {current_price:,.0f}", f"{change_5m}%")
                    st.success(f"**Signal:** {signal} | Score: {score}")
                    st.write(f"RSI: {round(rsi,1)} | VWAP: {round(vwap,2)}")
                    st.write(f"Entry: **{entry}** | SL: **{stop_loss}** | Target: **{target}** | R:R **1:{rr}**")

                with col2:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=data.index, y=data['Close'], name="Harga"))
                    fig.add_trace(go.Scatter(x=data.index, y=[vwap]*len(data), name="VWAP", line=dict(dash="dash")))
                    fig.update_layout(title=f"{ticker} - 5 Menit", height=400)
                    st.plotly_chart(fig, use_container_width=True)

            except Exception as e:
                st.error(f"Error {ticker}: {str(e)}")

st.caption("Refresh berkala saat pasar buka • Score ≥ 75 = sinyal kuat")
