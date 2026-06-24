import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, time
import pytz

st.set_page_config(page_title="Scalping Screener IDX - Auto", page_icon="🚀", layout="wide")

# ==================== TICKER LIST ====================
AUTO_TICKERS = [
    "BBCA.JK", "BBRI.JK", "BMRI.JK", "BBNI.JK", "TLKM.JK", "ASII.JK",
    "ADRO.JK", "AMMN.JK", "BUMI.JK", "ANTM.JK", "MDKA.JK", "PTBA.JK",
    "GOTO.JK", "BUKA.JK", "AMRT.JK", "KLBF.JK", "UNTR.JK", "ITMG.JK",
    "BRPT.JK", "DSSA.JK", "BREN.JK", "DEWA.JK", "CUAN.JK", "EXCL.JK",
    "ISAT.JK", "INDF.JK", "ICBP.JK", "TOWR.JK", "JSMR.JK", "MEDC.JK",
    "AKRA.JK", "CPIN.JK", "SMGR.JK", "UNVR.JK", "MBMA.JK"
]

# Cek jam pasar IDX
def is_market_open():
    tz = pytz.timezone('Asia/Jakarta')
    now = datetime.now(tz)
    current_time = now.time()
    
    # Senin-Kamis: 09:00 - 15:50
    # Jumat: 09:00 - 15:50 (istirahat lebih panjang)
    if now.weekday() >= 5:  # Sabtu & Minggu
        return False, "Pasar tutup (Weekend)"
    
    open_time = time(9, 0)
    close_time = time(15, 50)
    
    if open_time <= current_time <= close_time:
        return True, "Pasar BUKA"
    elif current_time < open_time:
        return False, f"Pasar belum buka. Buka pukul 09:00 WIB ({(datetime.combine(now.date(), open_time) - now).seconds//60} menit lagi)"
    else:
        return False, "Pasar sudah tutup hari ini"

# ==================== FETCH DATA DENGAN ERROR HANDLING ====================
def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1] if not rsi.empty else 50

@st.cache_data(ttl=30)
def fetch_stock_data(tickers):
    results = []
    market_open, status_msg = is_market_open()
    
    if not market_open:
        st.warning(f"⚠️ {status_msg}")
        return pd.DataFrame()  # kosong dulu
    
    progress = st.progress(0)
    
    for i, ticker in enumerate(tickers):
        try:
            t = yf.Ticker(ticker)
            hist_1m = t.history(period="1d", interval="1m")
            
            if hist_1m.empty:
                continue
                
            current_price = round(hist_1m['Close'].iloc[-1], 2)
            volume_today = int(hist_1m['Volume'].sum())
            
            # Change %
            hist_2d = t.history(period="2d", interval="1d")
            change_pct = round(((current_price - hist_2d['Close'].iloc[-2]) / hist_2d['Close'].iloc[-2] * 100), 2) if len(hist_2d) >= 2 else 0
            
            # Relative Volume
            hist_20d = t.history(period="20d", interval="1d")
            avg_vol = hist_20d['Volume'].mean() if not hist_20d.empty else volume_today
            rel_vol = round(volume_today / avg_vol, 2) if avg_vol > 0 else 1.0
            
            rsi = calculate_rsi(hist_20d['Close']) if not hist_20d.empty else 50
            
            signal = "Neutral"
            if change_pct > 1.5 and rel_vol > 2.0:
                signal = "🔥 Strong Momentum"
            elif change_pct < -1.5 and rel_vol > 2.0:
                signal = "📉 Strong Sell"
            elif rel_vol > 3.0:
                signal = "⚡ Volume Tinggi"
            
            results.append({
                "Ticker": ticker.replace(".JK", ""),
                "Harga": current_price,
                "Perubahan %": change_pct,
                "Volume": volume_today,
                "Rel Volume": rel_vol,
                "RSI": round(rsi, 1),
                "Signal": signal
            })
        except Exception as e:
            pass  # skip ticker bermasalah
        
        progress.progress((i + 1) / len(tickers))
    
    progress.empty()
    return pd.DataFrame(results)

# ==================== UI ====================
st.title("🚀 Scalping Screener IDX - Auto Mode")
st.caption(f"36 saham likuid terbaik • Update tiap 30 detik • {datetime.now().strftime('%d %b %Y %H:%M')} WIB")

market_open, msg = is_market_open()
st.info(f"**Status Pasar:** {msg}")

with st.sidebar:
    if st.button("🔄 Refresh Data Sekarang", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Fetch
df = fetch_stock_data(AUTO_TICKERS)

if df.empty:
    st.stop()

# Filter & Score
df["Score"] = df["Rel Volume"] * abs(df["Perubahan %"])

col1, col2 = st.columns(2)
with col1:
    min_rel = st.slider("Min Relative Volume", 0.5, 5.0, 1.5, 0.1)
with col2:
    min_change = st.slider("Min |Perubahan %|", 0.0, 10.0, 1.0, 0.2)

filtered = df[(df["Rel Volume"] >= min_rel) & (abs(df["Perubahan %"]) >= min_change)].copy()
filtered = filtered.sort_values("Score", ascending=False)

st.subheader("🏆 Top Emiten Scalping")
st.dataframe(filtered.head(10), use_container_width=True, hide_index=True)

# Chart
st.subheader("📈 Chart 5 Menit")
selected = st.selectbox("Pilih Ticker", filtered["Ticker"].tolist())
if selected:
    try:
        data = yf.download(selected+".JK", period="1d", interval="5m")
        fig = go.Figure([go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'])])
        fig.update_layout(title=f"{selected} - Intraday", height=500, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
    except:
        st.warning("Chart belum tersedia.")

st.caption("**Tips:** Buka aplikasi ini mulai jam 08.45 WIB supaya data langsung muncul saat pasar buka.")
