
import streamlit as st
import pandas as pd
import numpy as np
import datetime
import json
import requests
import matplotlib.pyplot as plt

# ================================
# 텔레그램 설정
# ================================
TELEGRAM_TOKEN = '7733325333:AAEQzQX-kZQFiNJi6pL87YJ8cQQtIOYtwhw'
CHAT_ID = '8115626217'

def send_telegram_message(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    try:
        requests.post(url, data=data)
    except:
        pass

# ================================
# 전략 설정 저장/불러오기
# ================================
STRATEGY_FILE = "nekito_strategy_config.json"

def load_strategy():
    try:
        with open(STRATEGY_FILE, "r") as f:
            return json.load(f)
    except:
        return {"rsi_threshold": 29, "volume_multiplier": 1.8, "hour_start": 3, "hour_end": 18}

def save_strategy(config):
    with open(STRATEGY_FILE, "w") as f:
        json.dump(config, f)

# ================================
# RSI 계산 함수
# ================================
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# ================================
# Streamlit 인터페이스
# ================================
st.title("📊 넥키토 전략 대시보드 (전략 저장 포함)")

config = load_strategy()
with st.sidebar:
    st.header("🎛 전략 설정")
    rsi_threshold = st.slider("RSI 임계값", 10, 50, config["rsi_threshold"])
    volume_multiplier = st.slider("거래량 배수", 1.0, 3.0, config["volume_multiplier"], step=0.1)
    hour_start = st.slider("시작 시간", 0, 23, config["hour_start"])
    hour_end = st.slider("종료 시간", 0, 23, config["hour_end"])

    # 전략 자동 저장
    new_config = {
        "rsi_threshold": rsi_threshold,
        "volume_multiplier": volume_multiplier,
        "hour_start": hour_start,
        "hour_end": hour_end
    }
    save_strategy(new_config)

uploaded_file = st.file_uploader("CSV 데이터 업로드", type=["csv"])
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df.set_index('datetime', inplace=True)
    df['rsi'] = calculate_rsi(df['close'])
    df['avg_volume'] = df['volume'].rolling(window=10).mean()
    df['hour'] = df.index.hour

    df['entry'] = (
        (df['rsi'] < rsi_threshold) &
        (df['volume'] > df['avg_volume'] * volume_multiplier) &
        (df['hour'].between(hour_start, hour_end))
    )

    trades = []
    for entry_time in df[df['entry']].index:
        exit_time = entry_time + pd.Timedelta(days=1)
        if exit_time in df.index:
            buy = df.loc[entry_time, "close"]
            sell = df.loc[exit_time, "close"]
            pnl = (sell - buy) / buy * 100
            trades.append({
                "entry": entry_time,
                "exit": exit_time,
                "buy_price": buy,
                "sell_price": sell,
                "pnl": pnl
            })

    result_df = pd.DataFrame(trades)
    st.subheader("📈 백테스트 결과")
    st.write(result_df.tail())

    success_rate = (result_df["pnl"] > 0).mean() * 100
    avg_return = result_df["pnl"].mean()
    st.metric("✅ 성공률", f"{success_rate:.2f}%")
    st.metric("📉 평균 수익률", f"{avg_return:.2f}%")

    if success_rate >= 90:
        send_telegram_message(
            f"📡 [Nekito Signal Alert]\n"
            f"✅ 조건 충족됨! 전략 매수 시점 도달\n"
            f"RSI < {rsi_threshold}, 볼륨 > {volume_multiplier}배\n"
            f"성공률: {success_rate:.2f}%, 평균 수익률: {avg_return:.2f}%"
        )

    # 수익률 히스토그램
    st.subheader("📊 수익률 분포 히스토그램")
    fig, ax = plt.subplots()
    result_df["pnl"].hist(bins=20, ax=ax)
    ax.set_title("Return Distribution (%)")
    ax.set_xlabel("수익률 (%)")
    ax.set_ylabel("거래 수")
    st.pyplot(fig)
