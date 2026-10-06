import os
import warnings
import datetime
import matplotlib.dates as mdates
import matplotlib.font_manager as fm
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import mplfinance as mpf
import numpy as np
import pandas as pd
from pykrx import stock
import pytz
import yfinance as yf
import re

# KRX 로그인 환경변수 설정 (github actions 환경 변수로 등록해도 됩니다)
os.environ["KRX_ID"] = "ihc1101"
os.environ["KRX_PW"] = "h20050601@"
warnings.filterwarnings("ignore")

# 한글 폰트 적용 (GitHub Actions 우분투 서버용 경로)
fontpath = "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf"
if os.path.exists(fontpath):
    fm.fontManager.addfont(fontpath)
    plt.rc("font", family="NanumBarunGothic")
plt.rcParams["axes.unicode_minus"] = False

# 15시 30분 기준 컷오프 날짜 계산
kst = pytz.timezone("Asia/Seoul")
now_kst = datetime.datetime.now(kst)

if (now_kst.hour, now_kst.minute) < (15, 30):
    cutoff_date = (now_kst - datetime.timedelta(days=1)).date()
else:
    cutoff_date = now_kst.date()

cutoff_str = cutoff_date.strftime("%Y-%m-%d")
weekdays = ["월", "화", "수", "목", "금", "토", "일"]
today_str = cutoff_date.strftime("%m%d") # 웹앱 호환을 위해 요일 제거 (ex. 1006)
formatted_date = cutoff_date.strftime("%m%d") + f"({weekdays[cutoff_date.weekday()]})"

print(f"⏰ 데이터 기준일: {cutoff_str} 15시 30분 (컷오프 적용)")
print("=" * 65)

print("📊 [1/2] 코스피 투자자별 누적 순매수 차트 수집 및 생성 중...")
start_date_2y = (cutoff_date - datetime.timedelta(days=730)).strftime("%Y%m%d")
end_date_str = cutoff_date.strftime("%Y%m%d")

try:
    df_investor = stock.get_market_trading_value_by_date(start_date_2y, end_date_str, "KOSPI")
    if not df_investor.empty:
        foreign_col = "외국인합계" if "외국인합계" in df_investor.columns else ("외국인" if "외국인" in df_investor.columns else None)
        inst_col = "기관합계" if "기관합계" in df_investor.columns else ("기관" if "기관" in df_investor.columns else None)
        person_col = "개인"

        cum_df = pd.DataFrame(index=df_investor.index)
        cum_df["외국인"] = df_investor[foreign_col].cumsum() / 1e12
        cum_df["기관"] = df_investor[inst_col].cumsum() / 1e12
        cum_df["개인"] = df_investor[person_col].cumsum() / 1e12

        kospi_df = yf.Ticker("^KS11").history(
            start=(cutoff_date - datetime.timedelta(days=730)).strftime("%Y-%m-%d"),
            end=(cutoff_date + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        )
        if getattr(kospi_df.index, "tz", None) is not None:
            kospi_df.index = kospi_df.index.tz_localize(None)
        kospi_close = kospi_df["Close"].reindex(cum_df.index, method="ffill")

        fig_inv, (ax_inv1, ax_inv2, ax_inv3) = plt.subplots(3, 1, figsize=(10, 18), facecolor="white", dpi=150)

        # 1) 최근 2년 누적 순매수
        ax_inv1.plot(cum_df.index, cum_df["외국인"], label="외국인 누적", color="#1f77b4", linewidth=2.2)
        ax_inv1.plot(cum_df.index, cum_df["기관"], label="기관 누적", color="#ff7f0e", linewidth=2.2)
        ax_inv1.plot(cum_df.index, cum_df["개인"], label="개인 누적", color="#d62728", linewidth=2.2)
        ax_inv1.axhline(0, color="gray", linestyle="--", linewidth=1, alpha=0.7)
        ax_inv1.set_ylabel("누적 순매수 (조 원)", fontsize=14, fontweight="bold")
        ax_inv1.legend(loc="upper left", fontsize=12)
        ax_inv1.grid(True, linestyle=":", alpha=0.6)

        ax_inv1_twin = ax_inv1.twinx()
        ax_inv1_twin.plot(cum_df.index, kospi_close, color="black", linestyle=":", linewidth=1.5, alpha=0.45, label="KOSPI 지수")
        ax_inv1.xaxis.set_major_formatter(mdates.DateFormatter("%y.%m.%d"))
        
        ax_inv1.text(0.02, 0.96, f"{formatted_date} 15시30분 기준", transform=ax_inv1.transAxes, fontsize=18, fontweight="heavy", bbox=dict(boxstyle="round,pad=0.4", facecolor="white", alpha=0.9))

        # 2) 최근 6개월
        df_6m = df_investor.iloc[-126:] if len(df_investor) > 126 else df_investor
        cum_6m = pd.DataFrame(index=df_6m.index)
        cum_6m["외국인"] = df_6m[foreign_col].cumsum() / 1e12
        cum_6m["기관"] = df_6m[inst_col].cumsum() / 1e12
        cum_6m["개인"] = df_6m[person_col].cumsum() / 1e12
        ax_inv2.plot(cum_6m.index, cum_6m["외국인"], label="외국인", color="#1f77b4", linewidth=2.0)
        ax_inv2.plot(cum_6m.index, cum_6m["기관"], label="기관", color="#ff7f0e", linewidth=2.0)
        ax_inv2.plot(cum_6m.index, cum_6m["개인"], label="개인", color="#d62728", linewidth=2.0)
        ax_inv2.axhline(0, color="gray", linestyle="--", linewidth=1)
        ax_inv2.xaxis.set_major_formatter(mdates.DateFormatter("%y.%m.%d"))

        # 3) 일일 막대
        df_recent = (df_investor.iloc[-20:] / 1e8) if len(df_investor) > 20 else (df_investor / 1e8)
        x_dates = df_recent.index
        width = 0.26
        x_indices = np.arange(len(x_dates))
        ax_inv3.bar(x_indices - width, df_recent[foreign_col], width=width, label="외국인", color="#1f77b4")
        ax_inv3.bar(x_indices, df_recent[inst_col], width=width, label="기관", color="#ff7f0e")
        ax_inv3.bar(x_indices + width, df_recent[person_col], width=width, label="개인", color="#d62728")
        ax_inv3.axhline(0, color="black", linewidth=1)
        step = max(1, len(x_dates) // 7)
        ax_inv3.set_xticks(x_indices[::step])
        ax_inv3.set_xticklabels([d.strftime("%y.%m.%d") for d in x_dates[::step]])

        plt.tight_layout()
        plt.savefig(f"코스피_투자자별_누적순매수_{today_str}.jpg", format="jpg", dpi=150, bbox_inches="tight")
        plt.close(fig_inv)
        print(" └ ✅ 코스피 수급 차트 생성 완료!")
except Exception as e:
    print(f" └ ⚠️ KRX 수급 데이터 수집 중 오류 발생: {e}")

print("\n📈 [2/2] 9대 주요 지표 차트 및 줌 차트 생성 중...")
ASSET_DICT = {
    "KOSPI": "^KS11", "KODEX 200타겟위클리커버드콜": "498400.KS", "TIGER배당커버드콜액티브": "472150.KS",
    "나스닥100": "^NDX", "TIME미국나스닥100액티브": "426030.KS", "원달러 환율": "KRW=X",
    "금 현물 (달러 기준)": "GC=F", "금 현물 (원화 기준)": "GOLD_KRW", "은 현물 (달러 기준)": "SI=F",
}

def get_historical_data(ticker, period, interval):
    if ticker == "GOLD_KRW":
        gold = yf.Ticker("GC=F").history(period=period, interval=interval)
        usdkrw = yf.Ticker("KRW=X").history(period=period, interval=interval)
        if gold.empty or usdkrw.empty: return pd.DataFrame()
        if getattr(gold.index, "tz", None) is not None: gold.index = gold.index.tz_localize(None)
        if getattr(usdkrw.index, "tz", None) is not None: usdkrw.index = usdkrw.index.tz_localize(None)
        usdkrw = usdkrw.reindex(gold.index, method="ffill")
        df = gold.copy()
        for col in ["Open", "High", "Low", "Close"]:
            df[col] = (gold[col] * usdkrw["Close"]) / 31.1034768
        df = df.dropna(subset=["Open", "High", "Low", "Close"])
    else:
        df = yf.Ticker(ticker).history(period=period, interval=interval)
        if df.empty: return df
        if getattr(df.index, "tz", None) is not None: df.index = df.index.tz_localize(None)
        df = df.dropna(subset=["Open", "High", "Low", "Close"])
    df = df[df.index.normalize() <= pd.to_datetime(cutoff_str)]
    return df

def sync_latest_bar(df_higher, df_daily):
    if df_higher.empty or df_daily.empty: return df_higher
    valid_daily = df_daily.dropna(subset=["Open", "High", "Low", "Close"])
    if valid_daily.empty: return df_higher
    d_open, d_high, d_low, d_close = valid_daily["Open"].iloc[-1], valid_daily["High"].iloc[-1], valid_daily["Low"].iloc[-1], valid_daily["Close"].iloc[-1]
    last_idx = df_higher.index[-1]
    h_open, h_high, h_low = df_higher.at[last_idx, "Open"], df_higher.at[last_idx, "High"], df_higher.at[last_idx, "Low"]
    df_higher.at[last_idx, "Open"] = d_open if pd.isna(h_open) else h_open
    df_higher.at[last_idx, "High"] = d_high if pd.isna(h_high) else max(h_high, d_high)
    df_higher.at[last_idx, "Low"] = d_low if pd.isna(h_low) else min(h_low, d_low)
    df_higher.at[last_idx, "Close"] = d_close
    return df_higher

def add_indicators(df, ma_list):
    if len(df) == 0: return df
    for ma in ma_list: df[f"MA_{ma}"] = df["Close"].rolling(window=ma).mean()
    std_20 = df["Close"].rolling(window=20).std()
    df["BB_Upper"] = df[f"MA_{ma_list[0]}"] + (std_20 * 2)
    df["BB_Lower"] = df[f"MA_{ma_list[0]}"] - (std_20 * 2)
    tenkan = (df["High"].rolling(window=9).max() + df["Low"].rolling(window=9).min()) / 2
    kijun = (df["High"].rolling(window=26).max() + df["Low"].rolling(window=26).min()) / 2
    df["Tenkan"], df["Kijun"] = tenkan, kijun
    if len(df) >= 2:
        last_date = df.index[-1]
        diff = df.index[-1] - df.index[-2]
        future_idx = [last_date + diff * i for i in range(1, 27)]
        future_df = pd.DataFrame(index=future_idx, columns=df.columns)
        df_ext = pd.concat([df, future_df])
        df_ext["Senkou_A"] = ((tenkan + kijun) / 2).reindex(df_ext.index).shift(26)
        df_ext["Senkou_B"] = ((df["High"].rolling(window=52).max() + df["Low"].rolling(window=52).min()) / 2).reindex(df_ext.index).shift(26)
        return df_ext
    return df

def draw_chart(df, ax, title, ma_list, mpf_style=None):
    real_data = df.dropna(subset=["Open", "High", "Low", "Close"])
    if len(real_data) < 2: return
    apds = []
    ma_colors = ["#FFA500", "#1E90FF", "#8B4513", "#000000"]
    for ma, color in zip(ma_list, ma_colors):
        if df[f"MA_{ma}"].notna().any(): apds.append(mpf.make_addplot(df[f"MA_{ma}"], ax=ax, color=color, width=1.2, alpha=0.8))
    
    mpf.plot(df, type="candle", ax=ax, addplot=apds, ylabel="", datetime_format="%y.%m.%d", xrotation=0)
    ax.text(0.02, 0.97, f"{formatted_date} 기준", transform=ax.transAxes, fontsize=22, fontweight="heavy", bbox=dict(boxstyle="round,pad=0.5", facecolor="white", alpha=0.85), zorder=10)
    ax.text(0.98, 0.97, title, transform=ax.transAxes, ha="right", fontsize=22, fontweight="heavy", bbox=dict(boxstyle="round,pad=0.5", facecolor="white", alpha=0.85), zorder=10)

for asset_name, ticker in ASSET_DICT.items():
    print(f" └ [{asset_name}] 처리 중...")
    df_full_daily = get_historical_data(ticker, period="5y", interval="1d")
    if df_full_daily.empty: continue
    df_full_weekly = sync_latest_bar(get_historical_data(ticker, period="10y", interval="1wk"), df_full_daily)
    df_full_monthly = sync_latest_bar(get_historical_data(ticker, period="25y", interval="1mo"), df_full_daily)

    ma_list = [20, 50, 100, 200]
    df_daily = add_indicators(df_full_daily, ma_list).iloc[-(250 + 26) :] if len(df_full_daily) > 276 else add_indicators(df_full_daily, ma_list)
    df_weekly = add_indicators(df_full_weekly, ma_list).iloc[-(52 + 26) :] if len(df_full_weekly) > 78 else add_indicators(df_full_weekly, ma_list)
    df_monthly = add_indicators(df_full_monthly, ma_list).iloc[-(24 + 26) :] if len(df_full_monthly) > 50 else add_indicators(df_full_monthly, ma_list)

    mc = mpf.make_marketcolors(up="r", down="b", edge="inherit", wick="inherit")
    s = mpf.make_mpf_style(marketcolors=mc, rc={"font.family": "NanumBarunGothic", "axes.unicode_minus": False})

    fig = mpf.figure(figsize=(10, 18), style=s)
    ax1 = fig.add_subplot(3, 1, 1); ax2 = fig.add_subplot(3, 1, 2); ax3 = fig.add_subplot(3, 1, 3)
    draw_chart(df_daily, ax1, f"{asset_name} (일봉)", ma_list, mpf_style=s)
    draw_chart(df_weekly, ax2, f"{asset_name} (주봉)", ma_list, mpf_style=s)
    draw_chart(df_monthly, ax3, f"{asset_name} (월봉)", ma_list, mpf_style=s)

    plt.tight_layout()
    plt.savefig(f"{asset_name}_{today_str}.jpg", format="jpg", dpi=150, bbox_inches="tight")
    plt.close(fig)

print("✅ 차트 이미지 생성이 모두 완료되었습니다!")

print("\n📝 어플(index.html)에 오늘 날짜 자동 추가 중...")
html_file = "index.html"
if os.path.exists(html_file):
    with open(html_file, "r", encoding="utf-8") as f:
        html = f.read()

    match = re.search(r"const DATES = \[(.*?)\];", html)
    if match:
        current_dates = match.group(1)
        if f"'{today_str}'" not in current_dates:
            new_dates = f"'{today_str}', " + current_dates if current_dates else f"'{today_str}'"
            new_html = html.replace(match.group(0), f"const DATES = [{new_dates}];")
            with open(html_file, "w", encoding="utf-8") as f:
                f.write(new_html)
            print(f"✅ index.html에 오늘 날짜 '{today_str}' 추가 완료!")
        else:
            print(f"ℹ️ 이미 오늘 날짜 '{today_str}'가 등록되어 있습니다.")
    else:
        print("⚠️ index.html에서 DATES 배열을 찾지 못했습니다.")
else:
    print("⚠️ index.html 파일이 없어 날짜 업데이트를 건너뜁니다.")

print("=" * 65)
print("🎉 모든 로봇 자동화 작업이 끝났습니다!")