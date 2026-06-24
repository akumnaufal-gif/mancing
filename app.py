import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Scalping IDX Harian", layout="wide", page_icon="⚡")
st.title("⚡ Scalping IDX - Mode Harian")
st.markdown("**Khusus untuk trading saat pasar buka (09:00 - 16:00 WIB)**")

st.sidebar.header("Pengaturan Scalping")
tickers_input = st.text_area("Masukkan Ticker (pisah koma)", 
    "BBCA, BBRI, BMRI, BBNI, TLKM, ASII, ADRO, BREN, DEWA, BUVA", height=90)

if st.button("🚀 Scan Scalping Sekarang", type="primary", use_container_width=True):
    with st.spinner("Mengambil data 5 menit..."):
        tickers = [t.strip().upper() + ".JK" for t in tickers_input.split(",") if t.strip()]
        
        results = []
        for ticker in tickers:
            try:
                data = yf.download(ticker, period="3d", interval="5m", progress=False)
                if len(data) < 40: 
                    continue

                last = data.iloc[-1]
                prev = data.iloc[-2]
                current_price = last['Close']

                # RSI
                delta = data['Close'].diff()
                gain = delta.where(delta > 0, 0).rolling(14).mean().iloc[-1]
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean().iloc[-1]
                rsi = 100 - (100 / (1 + gain/loss)) if loss != 0 else 50

                # MACD Fast
                exp1 = data['Close'].ewm(span=8, adjust=False).mean()
                exp2 = data['Close'].ewm(span=17, adjust=False).mean()
                macd_line = exp1 - exp2
                macd_signal = macd_line.ewm(span=9, adjust=False).mean()
                macd_hist = macd_line - macd_signal

                # VWAP
                data['TP'] = (data['High'] + data['Low'] + data['Close']) / 3
                data['VWAP'] = (data['TP'] * data['Volume']).cumsum() / data['Volume'].cumsum()
                vwap = data['VWAP'].iloc[-1]

                ema9 = data['Close'].ewm(span=9).mean().iloc[-1]
                ema21 = data['Close'].ewm(span=21).mean().iloc[-1]

                vol_ratio = round(data['Volume'].iloc[-1] / data['Volume'].tail(30).mean(), 2) if len(data) > 30 else 1.0

                change_5m = round(((current_price - prev['Close']) / prev['Close']) * 100, 2)

                # Sinyal Scalping
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

                # Entry & Risk Management
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

                results.append({
                    'Ticker': ticker.replace('.JK',''),
                    'Harga': round(current_price, 2),
                    'Change 5m %': change_5m,
                    'RSI': round(rsi, 1),
                    'MACD': "Bullish" if macd_hist.iloc[-1] > 0 else "Bearish",
                    'VWAP': round(vwap, 2),
                    'Signal': signal,
                    'Score': score,
                    'Entry': entry,
                    'Stop Loss': stop_loss,
                    'Target': target,
                    'R:R': f"1:{rr}",
                    'Vol Ratio': vol_ratio
                })
            except:
                continue

        # === PERBAIKAN ERROR ===
        if results:
            df = pd.DataFrame(results).sort_values('Score', ascending=False)
            st.subheader("⚡ Sinyal Scalping Saat Ini")
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.warning("Tidak ada data yang berhasil diambil. Coba lagi saat pasar buka atau cek ticker.")

st.caption("Data 5 menit • Refresh setiap beberapa menit saat pasar buka • Score ≥ 75 = sinyal kuat")
