import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import time

st.set_page_config(page_title="Scalping Screener IDX", page_icon="🚀", layout="wide")

# ==================== TICKER (kurangi dulu jadi 20 untuk lebih cepat) ====================
AUTO_TICKERS = [
    "BBCA.JK", "BBRI.JK", "BMRI.JK", "BBNI.JK", "TLKM.JK", "ASII.JK",
    "ADRO.JK", "AMMN.JK", "BUMI.JK", "ANTM.JK", "MDKA.JK", "PTBA.JK",
    "GOTO.JK", "BUKA.JK", "AMRT.JK", "KLBF.JK", "UNTR.JK", "ITMG.JK",
    "BRPT.JK", "DSSA.JK", "BREN.JK", "DEWA.JK", "CUAN.JK", "EXCL.JK",
    "ISAT.JK", "INDF.JK", "ICBP.JK", "TOWR.JK", "JSMR.JK", "MEDC.JK",
    "AKRA.JK", "CPIN.JK", "SMGR.JK", "UNVR.JK", "MBMA.JK", "AADI.JK",
    "ADMR.JK", "HRTA.JK", "ESSA.JK", "WIFI.JK", "BBTN.JK", "BNBR.JK",
    "TPIA.JK", "BYAN.JK", "PGAS.JK", "INDY.JK", "SMMA.JK", "PGEO.JK",
    "RAJA.JK", "TAPG.JK", "MCAS.JK", "GEMS.JK", "SRTG.JK", "BSDE.JK",
    "PWON.JK", "SMRA.JK", "LPKR.JK", "JPFA.JK", "SIDO.JK", "HEAL.JK",
    "NCKL.JK", "MBMA.JK", "BIRD.JK", "MEGA.JK", "ARTO.JK", "BTPS.JK",
    "BDMN.JK", "PNBN.JK"
]  # 20 ticker dulu (bisa ditambah lagi nanti)

def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = -delta.where(delta < 0, 0).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

@st.cache_data(ttl=30)
def fetch_stock_data(tickers):
    results = []
    progress_bar = st.progress(0, text="Mengambil data real-time...")
    
    for i, ticker in enumerate(tickers):
        try:
            data = yf.download(ticker, period="1d", interval="1m", progress=False, timeout=10)
            if data.empty:
                continue
                
            current = data['Close'].iloc[-1]
            volume_today = data['Volume'].sum()
            
            # Change %
            hist_day = yf.download(ticker, period="2d", interval="1d", progress=False)
            change_pct = ((current - hist_day['Close'].iloc[-2]) / hist_day['Close'].iloc[-2] * 100) if len(hist_day) >= 2 else 0
            
            # Rel Volume
            hist_vol = yf.download(ticker, period="20d", interval="1d", progress=False)
            avg_vol = hist_vol['Volume'].mean() if not hist_vol.empty else volume_today
            rel_vol = volume_today / avg_vol if avg_vol > 0 else 1
            
            rsi = calculate_rsi(hist_vol['Close']).iloc[-1] if not hist_vol.empty else 50
            
            signal = "Neutral"
            if change_pct > 1.5 and rel_vol > 2.0:
                signal = "🔥 Strong Momentum"
            elif change_pct < -1.5 and rel_vol > 2.0:
                signal = "📉 Strong Sell"
            elif rel_vol > 3.0:
                signal = "⚡ Volume Tinggi"
            
            results.append({
                "Ticker": ticker.replace(".JK", ""),
                "Harga": round(current, 2),
                "Perubahan %": round(change_pct, 2),
                "Volume": int(volume_today),
                "Rel Volume": round(rel_vol, 2),
                "RSI": round(rsi, 1),
                "Signal": signal
            })
        except:
            pass
        
        progress_bar.progress((i + 1) / len(tickers), text=f"Proses {ticker.replace('.JK','')} ({i+1}/{len(tickers)})")
        time.sleep(0.3)  # biar tidak terlalu agresif
    
    progress_bar.empty()
    return pd.DataFrame(results)

# ==================== UI ====================
st.title("🚀 Scalping Screener IDX - Auto Mode")
st.caption(f"Update tiap 30 detik • {datetime.now().strftime('%d %b %Y %H:%M')} WIB")

with st.sidebar:
    if st.button("🔄 Refresh Sekarang", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Fetch data
df = fetch_stock_data(AUTO_TICKERS)

if df.empty:
    st.error("Masih belum ada data. Coba refresh lagi dalam 1-2 menit (pasar baru buka).")
    st.stop()

df["Score"] = df["Rel Volume"] * abs(df["Perubahan %"])

# Filter
col1, col2 = st.columns(2)
with col1:
    min_rel = st.slider("Min Relative Volume", 0.5, 5.0, 1.3, 0.1)
with col2:
    min_change = st.slider("Min |Perubahan %|", 0.0, 10.0, 0.8, 0.1)

filtered = df[(df["Rel Volume"] >= min_rel) & (abs(df["Perubahan %"]) >= min_change)].copy()
filtered = filtered.sort_values("Score", ascending=False)

st.subheader("🏆 Top Emiten Scalping Saat Ini")
st.dataframe(filtered.head(10), use_container_width=True, hide_index=True)

# Chart
st.subheader("📈 Chart Intraday")
if not filtered.empty:
    selected = st.selectbox("Pilih Ticker", filtered["Ticker"].tolist())
    if selected:
        try:
            chart_data = yf.download(selected + ".JK", period="1d", interval="5m", progress=False)
            fig = go.Figure([go.Candlestick(x=chart_data.index,
                                            open=chart_data['Open'],
                                            high=chart_data['High'],
                                            low=chart_data['Low'],
                                            close=chart_data['Close'])])
            fig.update_layout(title=f"{selected} - 5 Menit", height=500, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
        except:
            st.warning("Chart belum tersedia.")
else:
    st.info("Belum ada saham yang memenuhi filter.")

st.caption("**Tips:** Turunkan filter Min Rel Volume ke 1.0 atau Min Perubahan % ke 0.5 kalau masih kosong.")
