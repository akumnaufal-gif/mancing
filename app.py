import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, time
import pytz

st.set_page_config(page_title="Scalping Screener IDX", page_icon="🚀", layout="wide")

# ==================== TICKER LIST (65 ticker) ====================
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
    "NCKL.JK", "BIRD.JK", "MEGA.JK", "ARTO.JK", "BTPS.JK", "BDMN.JK", "PNBN.JK"
]

# ==================== WAKTU WIB & STATUS PASAR ====================
def get_wib_time():
    wib = pytz.timezone('Asia/Jakarta')
    return datetime.now(wib)

def is_market_open():
    now = get_wib_time()
    current_time = now.time()
    weekday = now.weekday()

    if weekday >= 5:  # Sabtu & Minggu
        return False, "🔴 Pasar TUTUP (Weekend)"
    
    open_time = time(9, 0)
    close_time = time(15, 50)
    
    if open_time <= current_time <= close_time:
        return True, "🟢 Pasar SEDANG BUKA"
    elif current_time < open_time:
        return False, f"🔴 Pasar belum buka (buka pukul 09:00 WIB)"
    else:
        return False, "🔴 Pasar sudah TUTUP hari ini"

# ==================== FETCH DATA ====================
@st.cache_data(ttl=25)
def fetch_stock_data(tickers):
    results = []
    progress_bar = st.progress(0, text="Mengambil data real-time...")

    for i, ticker in enumerate(tickers):
        try:
            data = yf.download(ticker, period="1d", interval="1m", progress=False, timeout=8)
            if data.empty:
                continue

            current = data['Close'].iloc[-1]
            volume_today = int(data['Volume'].sum())

            hist_day = yf.download(ticker, period="2d", interval="1d", progress=False)
            change_pct = ((current - hist_day['Close'].iloc[-2]) / hist_day['Close'].iloc[-2] * 100) if len(hist_day) >= 2 else 0

            hist_vol = yf.download(ticker, period="20d", interval="1d", progress=False)
            avg_vol = float(hist_vol['Volume'].mean()) if not hist_vol.empty else volume_today
            rel_vol = volume_today / avg_vol if avg_vol > 0 else 1.0

            # RSI
            delta = hist_vol['Close'].diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = -delta.where(delta < 0, 0).rolling(14).mean()
            rs = gain / loss
            rsi_val = round(100 - (100 / (1 + rs)).iloc[-1], 1) if not rs.empty else 50

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
                "Volume": volume_today,
                "Rel Volume": round(rel_vol, 2),
                "RSI": rsi_val,
                "Signal": signal
            })
        except:
            pass

        progress_bar.progress((i + 1) / len(tickers), text=f"{ticker.replace('.JK','')}")

    progress_bar.empty()
    return pd.DataFrame(results)

# ==================== UI ====================
st.title("🚀 Scalping Screener IDX - Auto Mode")

wib_now = get_wib_time()
st.caption(f"65 saham likuid terbaik • Update tiap 25 detik • {wib_now.strftime('%d %b %Y %H:%M:%S')} WIB")

market_open, market_status = is_market_open()
st.info(f"**Status Pasar:** {market_status}")

with st.sidebar:
    if st.button("🔄 Refresh Data Sekarang", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Ambil data
df = fetch_stock_data(AUTO_TICKERS)

if df.empty:
    st.warning("⏳ Belum ada data yang terambil. Klik Refresh lagi atau tunggu sebentar.")
    st.stop()

df["Score"] = df["Rel Volume"] * abs(df["Perubahan %"])

col1, col2 = st.columns(2)
with col1:
    min_rel = st.slider("Min Relative Volume", 0.5, 5.0, 1.0, 0.1)
with col2:
    min_change = st.slider("Min |Perubahan %|", 0.0, 10.0, 0.5, 0.1)

filtered = df[(df["Rel Volume"] >= min_rel) & (abs(df["Perubahan %"]) >= min_change)].copy()
filtered = filtered.sort_values("Score", ascending=False)

st.subheader("🏆 Top 10 Emiten Scalping Saat Ini")
st.dataframe(filtered.head(10), use_container_width=True, hide_index=True)

# Chart
st.subheader("📈 Chart Intraday")
if not filtered.empty:
    selected = st.selectbox("Pilih Ticker", filtered["Ticker"].tolist())
    if selected:
        try:
            chart_data = yf.download(selected + ".JK", period="1d", interval="5m", progress=False)
            fig = go.Figure([go.Candlestick(x=chart_data.index, open=chart_data['Open'],
                                            high=chart_data['High'], low=chart_data['Low'], close=chart_data['Close'])])
            fig.update_layout(title=f"{selected} - 5 Menit Chart", height=500, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
        except:
            st.warning("Chart belum tersedia.")
