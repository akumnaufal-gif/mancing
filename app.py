import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, time
import pytz

st.set_page_config(page_title="Scalping Screener IDX", page_icon="🚀", layout="wide")

# ==================== TICKER LIST ====================
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

def get_wib_time():
    return datetime.now(pytz.timezone('Asia/Jakarta'))

def is_market_open():
    now = get_wib_time()
    current = now.time()
    if now.weekday() >= 5:
        return False, "🔴 Pasar TUTUP (Weekend)"
    if time(9,0) <= current <= time(15,50):
        return True, "🟢 Pasar SEDANG BUKA"
    return False, "🔴 Pasar TUTUP"

# ==================== FETCH DATA ====================
@st.cache_data(ttl=20)
def fetch_stock_data(tickers):
    results = []
    progress = st.progress(0, text="Mengambil data...")

    for i, ticker in enumerate(tickers):
        try:
            # Data intraday
            data = yf.download(ticker, period="1d", interval="1m", progress=False, timeout=10)
            if data.empty:
                continue

            current = data['Close'].iloc[-1]
            volume_today = int(data['Volume'].sum())

            # Change %
            day_data = yf.download(ticker, period="2d", interval="1d", progress=False)
            change_pct = ((current - day_data['Close'].iloc[-2]) / day_data['Close'].iloc[-2] * 100) if len(day_data) >= 2 else 0.0

            # Relative Volume
            vol_data = yf.download(ticker, period="20d", interval="1d", progress=False)
            avg_vol = float(vol_data['Volume'].mean()) if not vol_data.empty else volume_today
            rel_vol = volume_today / avg_vol if avg_vol > 0 else 1.0

            # RSI
            delta = vol_data['Close'].diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = -delta.where(delta < 0, 0).rolling(14).mean()
            rs = gain / loss
            rsi = round(100 - (100 / (1 + rs)).iloc[-1], 1) if not rs.empty else 50

            signal = "Neutral"
            if abs(change_pct) > 1.0 and rel_vol > 1.5:
                signal = "🔥 Momentum Kuat" if change_pct > 0 else "📉 Sell Momentum"
            elif rel_vol > 2.5:
                signal = "⚡ Volume Tinggi"

            results.append({
                "Ticker": ticker.replace(".JK", ""),
                "Harga": round(current, 2),
                "Perubahan %": round(change_pct, 2),
                "Volume": volume_today,
                "Rel Volume": round(rel_vol, 2),
                "RSI": rsi,
                "Signal": signal
            })
        except:
            pass

        progress.progress((i+1)/len(tickers))

    progress.empty()
    return pd.DataFrame(results)

# ==================== UI ====================
st.title("🚀 Scalping Screener IDX - Auto Mode")
wib = get_wib_time()
st.caption(f"65 saham likuid • Update tiap 20 detik • {wib.strftime('%d %b %Y %H:%M:%S')} WIB")

market_open, status = is_market_open()
st.info(f"**Status Pasar:** {status}")

with st.sidebar:
    if st.button("🔄 Refresh Data Sekarang", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

df = fetch_stock_data(AUTO_TICKERS)

if df.empty:
    st.error("🚫 Masih belum ada data sama sekali. Klik Refresh beberapa kali atau tunggu sampai jam 09:30 WIB.")
    st.stop()

df["Score"] = df["Rel Volume"] * abs(df["Perubahan %"])

# Filter yang lebih longgar
col1, col2 = st.columns(2)
with col1:
    min_rel = st.slider("Min Relative Volume", 0.5, 5.0, 0.8, 0.1)   # lebih longgar
with col2:
    min_change = st.slider("Min |Perubahan %|", 0.0, 10.0, 0.3, 0.1) # lebih longgar

filtered = df[(df["Rel Volume"] >= min_rel) & (abs(df["Perubahan %"]) >= min_change)].copy()
filtered = filtered.sort_values("Score", ascending=False)

st.subheader(f"🏆 Top Emiten Scalping ({len(filtered)} saham terfilter)")
st.dataframe(filtered.head(15), use_container_width=True, hide_index=True)

# Chart
st.subheader("📈 Chart 5 Menit")
if not filtered.empty:
    selected = st.selectbox("Pilih Ticker", filtered["Ticker"].tolist())
    try:
        chart = yf.download(selected + ".JK", period="1d", interval="5m", progress=False)
        fig = go.Figure([go.Candlestick(x=chart.index, open=chart['Open'], high=chart['High'],
                                        low=chart['Low'], close=chart['Close'])])
        fig.update_layout(title=f"{selected} - 5 Menit", height=500, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
    except:
        st.warning("Chart tidak tersedia untuk saat ini.")
