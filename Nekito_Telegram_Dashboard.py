
import streamlit as st
import pandas as pd
import datetime
import requests
import numpy as np

# ================================
# 텔레그램 알림 설정
# ================================
TELEGRAM_TOKEN = '7733325333:AAEQzQX-kZQFiNJi6pL87YJ8cQQtIOYtwhw'
CHAT_ID = '8115626217'

def send_telegram_message(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": msg
    }
    try:
        requests.post(url, data=data)
    except Exception as e:
        st.warning(f"❌ 텔레그램 알림 실패: {e}")

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
st.title("📊 넥키토 실시간 전략 대시보드 (알림 포함)")

uploaded_file = st.file_uploader("CSV 데이터 업로드", type=["csv"])
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df.set_index('datetime', inplace=True)
    df['rsi'] = calculate_rsi(df['close'])
    df['avg_volume'] = df['volume'].rolling(window=10).mean()
    df['hour'] = df.index.hour

    # 조건 설정
    RSI_THRESHOLD = 29
    VOL_MULT = 1.8
    HOUR_START, HOUR_END = 3, 18

    df['entry'] = (
        (df['rsi'] < RSI_THRESHOLD) &
        (df['volume'] > df['avg_volume'] * VOL_MULT) &
        (df['hour'].between(HOUR_START, HOUR_END))
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
                "pnl": pnl,
                "result": "SUCCESS" if pnl > 0 else "FAILURE"
            })

    result_df = pd.DataFrame(trades)
    success_rate = (result_df["pnl"] > 0).mean() * 100
    avg_return = result_df["pnl"].mean()

    st.subheader("📈 백테스트 결과")
    st.write(result_df.tail())
    st.metric("✅ 성공률", f"{success_rate:.2f}%")
    st.metric("📈 평균 수익률", f"{avg_return:.2f}%")

    if success_rate >= 90:
        send_telegram_message(
            f"📡 [Nekito Signal Alert]\n"
            f"✅ 조건 충족됨!\n"
            f"RSI < {RSI_THRESHOLD}, 볼륨 > {VOL_MULT}배\n"
            f"성공률: {success_rate:.2f}%, 평균 수익률: {avg_return:.2f}%"
        )
        st.success("✅ 텔레그램 알림이 전송되었습니다.")
