import pandas as pd
import itertools
import json

# ---------------------------
# 전략 진화 설정
# ---------------------------
def generate_condition_combinations():
    rsi_list = range(15, 40)
    vol_list = [1.2, 1.4, 1.6, 1.8, 2.0, 2.2]
    hour_start_list = range(0, 12, 2)
    hour_end_list = range(12, 24, 2)

    return list(itertools.product(rsi_list, vol_list, hour_start_list, hour_end_list))

# ---------------------------
# 전략 테스트
# ---------------------------
def test_conditions(df, rsi, vol, hour_start, hour_end):
    df['hour'] = df.index.hour
    df['avg_volume'] = df['volume'].rolling(window=10).mean()
    df['rsi'] = calculate_rsi(df['close'])

    df['entry'] = (
        (df['rsi'] < rsi) &
        (df['volume'] > df['avg_volume'] * vol) &
        (df['hour'].between(hour_start, hour_end))
    )

    trades = []
    for entry_time in df[df['entry']].index:
        exit_time = entry_time + pd.Timedelta(days=1)
        if exit_time in df.index:
            buy = df.loc[entry_time, "close"]
            sell = df.loc[exit_time, "close"]
            pnl = (sell - buy) / buy * 100
            trades.append(pnl)

    if trades:
        return {
            "RSI": rsi,
            "VolMult": vol,
            "HourStart": hour_start,
            "HourEnd": hour_end,
            "SuccessRate": (pd.Series(trades) > 0).mean() * 100,
            "AvgReturn": pd.Series(trades).mean(),
            "Count": len(trades)
        }
    return None

# ---------------------------
# RSI 계산 함수
# ---------------------------
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# ---------------------------
# 전략 진화 루프
# ---------------------------
def evolve_strategies(df):
    combinations = generate_condition_combinations()
    results = []

    for i, (rsi, vol, h_start, h_end) in enumerate(combinations):
        result = test_conditions(df.copy(), rsi, vol, h_start, h_end)
        if result and result["SuccessRate"] >= 90 and result["AvgReturn"] > 0:
            results.append(result)
        if i % 50 == 0:
            print(f"테스트 진행 중... ({i}/{len(combinations)})")

    if results:
        results_df = pd.DataFrame(results).sort_values(by="SuccessRate", ascending=False)
        best = results_df.iloc[0]

        # 저장
        with open("nekito_strategy_config.json", "w") as f:
            json.dump({
                "rsi_threshold": best["RSI"],
                "volume_multiplier": best["VolMult"],
                "hour_start": best["HourStart"],
                "hour_end": best["HourEnd"]
            }, f)

        print("✅ 성공률 90% 이상 조건 저장 완료:", best)

    else:
        print("❌ 조건 중 성공률 90% 이상 전략 없음.")