import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Scalping Screener IDX", page_icon="🚀", layout="wide")

# ==================== DEFAULT TICKERS (LQ45 + High Volume) ====================
DEFAULT_TICKERS = [
    "BBCA.JK", "BBRI.JK", "BMRI.JK", "BBNI.JK", "TLKM.JK",
    "ADRO.JK", "ADMR.JK", "AMMN.JK", "ASII.JK", "GOTO.JK",
    "BUMI.JK", "DEWA.JK", "ICBP.JK", "INDF.JK", "UNVR.JK",
    "KLBF.JK", "EXCL.JK", "ISAT.JK", "ITMG.JK", "UNTR.JK",
    "TOWR.JK", "PTBA.JK", "BRPT.JK", "AMRT.JK", "CUAN.JK"
]

# ==================== FUNGSI HELPER ====================
def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

@st.cache_data(ttl=60)  # Cache 60 detik (bisa diubah)
def fetch_stock_data(tickers):
    results = []
    progress = st.progress(0)
    
    for i, ticker in enumerate(tickers):
        try:
            t = yf.Ticker(ticker)
            
            # Data intraday hari ini (untuk volume & harga terkini)
            hist_1m = t.history(period="1d", interval="1m")
            if hist_1m.empty:
                continue
                
            current_price = hist_1m['Close'].iloc[-1]
            volume_today = hist_1m['Volume'].sum()
            
            # Perubahan % dari close kemarin
            hist_2d = t.history(period="2d", interval="1d")
            if len(hist_2d) >= 2:
                prev_close = hist_2d['Close'].iloc[-2]
                change_pct = ((current_price - prev_close) / prev_close) * 100
            else:
                change_pct = 0
            
            # Relative Volume (vs rata-rata 20 hari)
            hist_20d = t.history(period="1mo", interval="1d")
            avg_vol = hist_20d['Volume'].mean() if not hist_20d.empty else volume_today
            rel_vol = volume_today / avg_vol if avg_vol > 0 else 1
            
            # RSI 14 (daily)
            hist_rsi = t.history(period="3mo", interval="1d")
            rsi = calculate_rsi(hist_rsi['Close']) if len(hist_rsi) > 14 else 50
            
            # Signal sederhana untuk scalping
            signal = "Neutral"
            if change_pct > 1.8 and rel_vol > 2.0:
                signal = "🔥 Strong Momentum"
            elif change_pct < -1.8 and rel_vol > 2.0:
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
            
        except Exception as e:
            st.warning(f"Gagal ambil data {ticker}: {str(e)}")
        
        progress.progress((i + 1) / len(tickers))
    
    progress.empty()
    return pd.DataFrame(results)

# ==================== UI ====================
st.title("🚀 Real-time Scalping Screener IDX")
st.caption(f"Data via Yahoo Finance • Update otomatis setiap ~60 detik • {datetime.now().strftime('%d %b %Y %H:%M')} WIB")

st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("⚙️ Pengaturan")
    
    tickers_input = st.text_area(
        "Daftar Ticker (pisahkan dengan koma)",
        value=", ".join(DEFAULT_TICKERS),
        height=150,
        help="Contoh: BBCA.JK, BBRI.JK, ADRO.JK"
    )
    
    tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
    
    if st.button("🔄 Refresh Data Sekarang", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    st.markdown("---")
    st.info("**Tips Scalping:**\n- Fokus ke Rel Volume > 2.0\n- Perubahan % > 1.5%\n- Volume tinggi = likuiditas bagus")

# Main Content
if not tickers:
    st.warning("Masukkan minimal 1 ticker!")
    st.stop()

with st.spinner("Mengambil data real-time..."):
    df = fetch_stock_data(tickers)

if df.empty:
    st.error("Tidak ada data yang berhasil diambil.")
    st.stop()

# Filter
col1, col2, col3 = st.columns(3)
with col1:
    min_rel_vol = st.slider("Min Relative Volume", 0.5, 5.0, 1.2, 0.1)
with col2:
    min_change = st.slider("Min |Perubahan %|", 0.0, 10.0, 0.8, 0.2)
with col3:
    sort_option = st.selectbox(
        "Urutkan berdasarkan",
        ["Perubahan %", "Rel Volume", "Volume", "RSI"],
        index=1
    )

# Filter data
filtered_df = df[
    (df["Rel Volume"] >= min_rel_vol) & 
    (abs(df["Perubahan %"]) >= min_change)
].copy()

if filtered_df.empty:
    st.warning("Tidak ada saham yang memenuhi filter.")
else:
    # Sort
    ascending = sort_option == "RSI"
    filtered_df = filtered_df.sort_values(by=sort_option, ascending=ascending)

    # Styling tabel
    def highlight_change(val):
        if val > 0:
            return "color: #00C853; font-weight: bold"
        elif val < 0:
            return "color: #FF1744; font-weight: bold"
        return ""

    styled_df = filtered_df.style.applymap(highlight_change, subset=["Perubahan %"])
    
    st.subheader("📊 Tabel Emiten")
    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Volume": st.column_config.NumberColumn(format="%d"),
            "Rel Volume": st.column_config.NumberColumn(format="%.2f"),
        }
    )

# ==================== EMITEN TERBAIK ====================
st.subheader("🏆 Emiten Terbaik untuk Scalping Saat Ini")

if not filtered_df.empty:
    filtered_df["Score"] = filtered_df["Rel Volume"] * abs(filtered_df["Perubahan %"])
    best_df = filtered_df.sort_values("Score", ascending=False).head(5)
    
    st.dataframe(
        best_df[["Ticker", "Harga", "Perubahan %", "Rel Volume", "Signal"]],
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("Tidak ada emiten yang memenuhi kriteria filter.")

# ==================== CHART DETAIL ====================
st.markdown("---")
st.subheader("📈 Chart Intraday (Pilih Ticker)")

selected_ticker = st.selectbox(
    "Pilih Ticker untuk melihat chart",
    options=df["Ticker"].tolist()
)

if selected_ticker:
    full_ticker = selected_ticker + ".JK"
    try:
        hist = yf.download(full_ticker, period="1d", interval="5m", progress=False)
        if not hist.empty:
            fig = go.Figure(data=[go.Candlestick(
                x=hist.index,
                open=hist['Open'],
                high=hist['High'],
                low=hist['Low'],
                close=hist['Close'],
                name=selected_ticker
            )])
            fig.update_layout(
                title=f"{selected_ticker} - Chart 5 Menit",
                xaxis_rangeslider_visible=False,
                height=500
            )
            st.plotly_chart(fig, use_container_width=True)
    except:
        st.error("Gagal menampilkan chart.")

# Disclaimer
st.markdown("---")
st.caption("""
**Disclaimer:**  
Data dari Yahoo Finance (bukan real-time murni).  
Aplikasi ini hanya untuk **analisis**, **bukan saran beli/jual**.  
Trading scalping berisiko tinggi. Gunakan manajemen risiko yang baik.
""")
