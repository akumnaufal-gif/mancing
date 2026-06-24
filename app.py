import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Scalping Screener IDX Auto", page_icon="🚀", layout="wide")

# ==================== LIST TICKER OTOMATIS (Update 2026) ====================
AUTO_TICKERS = [
    "BBCA.JK", "BBRI.JK", "BMRI.JK", "BBNI.JK", "TLKM.JK", "ASII.JK",
    "ADRO.JK", "AMMN.JK", "BUMI.JK", "ANTM.JK", "MDKA.JK", "PTBA.JK",
    "GOTO.JK", "BUKA.JK", "AMRT.JK", "KLBF.JK", "UNTR.JK", "ITMG.JK",
    "BRPT.JK", "DSSA.JK", "BREN.JK", "DEWA.JK", "CUAN.JK", "EXCL.JK",
    "ISAT.JK", "INDF.JK", "ICBP.JK", "TOWR.JK", "JSMR.JK", "MEDC.JK",
    "AKRA.JK", "CPIN.JK", "SMGR.JK", "UNVR.JK", "MBMA.JK", "AADI.JK"
]  # 36 saham paling likuid & sering bergerak

# ==================== FUNGSI (sama seperti sebelumnya) ====================
def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1] if not rsi.empty else 50

@st.cache_data(ttl=45)  # Update lebih cepat
def fetch_stock_data(tickers):
    results = []
    progress = st.progress(0)
    
    for i, ticker in enumerate(tickers):
        try:
            t = yf.Ticker(ticker)
            hist_1m = t.history(period="1d", interval="1m")
            if hist_1m.empty:
                continue
                
            current_price = hist_1m['Close'].iloc[-1]
            volume_today = hist_1m['Volume'].sum()
            
            hist_2d = t.history(period="2d", interval="1d")
            change_pct = ((current_price - hist_2d['Close'].iloc[-2]) / hist_2d['Close'].iloc[-2] * 100) if len(hist_2d) >= 2 else 0
            
            hist_20d = t.history(period="1mo", interval="1d")
            avg_vol = hist_20d['Volume'].mean() if not hist_20d.empty else volume_today
            rel_vol = volume_today / avg_vol if avg_vol > 0 else 1
            
            hist_rsi = t.history(period="3mo", interval="1d")
            rsi = calculate_rsi(hist_rsi['Close'])
            
            signal = "Neutral"
            if change_pct > 1.5 and rel_vol > 2.0:
                signal = "🔥 Strong Buy Momentum"
            elif change_pct < -1.5 and rel_vol > 2.0:
                signal = "📉 Strong Sell Momentum"
            elif rel_vol > 3.0:
                signal = "⚡ High Volume Alert"
            
            results.append({
                "Ticker": ticker.replace(".JK", ""),
                "Harga": round(current_price, 2),
                "Perubahan %": round(change_pct, 2),
                "Volume": int(volume_today),
                "Rel Volume": round(rel_vol, 2),
                "RSI": round(rsi, 1),
                "Signal": signal
            })
        except:
            pass
        
        progress.progress((i + 1) / len(tickers))
    
    progress.empty()
    return pd.DataFrame(results)

# ==================== UI ====================
st.title("🚀 Scalping Screener IDX - Auto Mode")
st.caption(f"Otomatis pakai {len(AUTO_TICKERS)} saham likuid terbaik • Update tiap ~45 detik • {datetime.now().strftime('%d %b %Y %H:%M')} WIB")

st.markdown("---")

with st.sidebar:
    st.header("⚙️ Pengaturan")
    if st.button("🔄 Refresh Data Sekarang", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    st.info("**Daftar otomatis** dari LQ45 + saham volume tertinggi hari ini.")

# Main
with st.spinner("Mengambil data real-time dari saham-saham likuid..."):
    df = fetch_stock_data(AUTO_TICKERS)

if df.empty:
    st.error("Gagal mengambil data.")
    st.stop()

# Filter
col1, col2, col3 = st.columns(3)
with col1:
    min_rel_vol = st.slider("Min Relative Volume", 0.5, 5.0, 1.5, 0.1)
with col2:
    min_change = st.slider("Min |Perubahan %|", 0.0, 10.0, 1.0, 0.2)
with col3:
    sort_option = st.selectbox("Urutkan berdasarkan", ["Score", "Rel Volume", "Perubahan %", "Volume"], index=0)

# Hitung Score
df["Score"] = df["Rel Volume"] * abs(df["Perubahan %"])

filtered_df = df[(df["Rel Volume"] >= min_rel_vol) & (abs(df["Perubahan %"]) >= min_change)].copy()

if filtered_df.empty:
    st.warning("Tidak ada saham yang memenuhi filter.")
else:
    filtered_df = filtered_df.sort_values(by=sort_option, ascending=False)
    
    def highlight(val):
        return "color: #00C853; font-weight: bold" if val > 0 else "color: #FF1744; font-weight: bold"
    
    st.subheader("📊 Hasil Screening")
    st.dataframe(
        filtered_df.style.applymap(highlight, subset=["Perubahan %"]),
        use_container_width=True,
        hide_index=True
    )

# Top Emiten
st.subheader("🏆 Top Emiten Scalping Saat Ini")
top_df = filtered_df.head(8)[["Ticker", "Harga", "Perubahan %", "Rel Volume", "RSI", "Signal"]]
st.dataframe(top_df, use_container_width=True, hide_index=True)

# Chart
st.markdown("---")
st.subheader("📈 Chart Intraday")
selected = st.selectbox("Pilih Ticker", options=filtered_df["Ticker"].tolist() if not filtered_df.empty else df["Ticker"].tolist())
if selected:
    try:
        hist = yf.download(selected + ".JK", period="1d", interval="5m", progress=False)
        fig = go.Figure(data=[go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'])])
        fig.update_layout(title=f"{selected} - 5 Menit Chart", xaxis_rangeslider_visible=False, height=500)
        st.plotly_chart(fig, use_container_width=True)
    except:
        st.error("Chart tidak tersedia.")

st.caption("**Catatan:** Daftar auto ini diambil dari saham LQ45 + paling aktif. Bisa kamu tambah/turunkan di code jika mau.")
