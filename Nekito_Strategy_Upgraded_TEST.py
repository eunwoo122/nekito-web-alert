import streamlit as st
import pandas as pd
import numpy as np
import datetime
import json
import requests
import matplotlib.pyplot as plt
import pyupbit

# ================================
# 텔레그램 설정
# ================================
TELEGRAM_TOKEN = st.secrets.get("TELEGRAM_TOKEN", "")
CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", "")

def send_telegram_message(msg):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    try:
        requests.post(url, data=data)
    except:
        pass

# ================================
# 업비트 자동매매 - 테스트 모드
# ================================
access_key = st.secrets.get("UPBIT_ACCESS_KEY", "")
secret_key = st.secrets.get("UPBIT_SECRET_KEY", "")
upbit = pyupbit.Upbit(access_key, secret_key)

TEST_MODE = True  # 실전 매매는 False로 설정

def execute_buy(symbol="KRW-SOL", krw=10000):
    if TEST_MODE:
        st.info(f"🧪 [테스트] {symbol} 가상 매수 실행됨 - 금액: {krw}원")
        send_telegram_message(f"📩 [TEST] {symbol} 매수 조건 충족 (금액: {krw}원)\n(실제 주문은 실행되지 않았습니다)")
        return {"status": "test_buy", "symbol": symbol, "amount": krw}
    else:
        return upbit.buy_market_order(symbol, krw)

def execute_sell(symbol="KRW-SOL", volume=1.0, return_rate=7.2):
    if TEST_MODE:
        st.info(f"🧪 [테스트] {symbol} 가상 매도 - 수익률: {return_rate}%")
        send_telegram_message(f"📤 [TEST] {symbol} 가상 매도 완료\n수익률: {return_rate:.2f}%")
        return {"status": "test_sell", "symbol": symbol, "return": return_rate}
    else:
        return upbit.sell_market_order(symbol, volume)

# ================================
# 전략 불러오기
# ================================
STRATEGY_FILE = "nekito_strategy_config.json"

def load_strategy():
    try:
        with open(STRATEGY_FILE, "r") as f:
            return json.load(f)
    except:
        return {"rsi_threshold": 29, "volume_multiplier": 1.8, "hour_start": 3, "hour_end": 18}

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
st.title("📊 넥키토 자동매매 대시보드 (테스트 모드)")

config = load_strategy()
with st.sidebar:
    st.header("🎛 전략 설정")
    rsi_threshold = st.slider("RSI 임계값", 10, 50, config["rsi_threshold"])
    volume_multiplier = st.slider("거래량 배수", 1.0, 3.0, config["volume_multiplier"], step=0.1)
    hour_start = st.slider("시작 시간", 0, 23, config["hour_start"])
    hour_end = st.slider("종료 시간", 0, 23, config["hour_end"])

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
            # 자동매매 테스트 실행
            execute_buy()
            execute_sell(return_rate=pnl)

    result_df = pd.DataFrame(trades)
    st.subheader("📈 백테스트 결과")
    st.write(result_df.tail())

    success_rate = (result_df["pnl"] > 0).mean() * 100
    avg_return = result_df["pnl"].mean()
    st.metric("✅ 성공률", f"{success_rate:.2f}%")
    st.metric("📉 평균 수익률", f"{avg_return:.2f}%")

    # 수익률 히스토그램
    st.subheader("📊 수익률 분포 히스토그램")
    fig, ax = plt.subplots()
    result_df["pnl"].hist(bins=20, ax=ax)
    ax.set_title("Return Distribution (%)")
    ax.set_xlabel("수익률 (%)")
    ax.set_ylabel("거래 수")
    st.pyplot(fig)