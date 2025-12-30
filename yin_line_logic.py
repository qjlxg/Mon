import pandas as pd
import numpy as np
import os
import glob
from datetime import datetime

# --- 配置 ---
DATA_DIR = 'stock_data'
OUTPUT_DIR = 'results/online_yin_pro'
NAMES_FILE = 'stock_names.csv'

def get_indicators(df):
    df = df.copy()
    # 核心均线系统
    for m in [5, 10, 20, 30, 60]:
        df[f'ma{m}'] = df['close'].rolling(m).mean()
    
    # 计算均线粘合度 (5, 10, 20日线标准差越小越粘合)
    df['ma_std'] = df[['ma5', 'ma10', 'ma20']].std(axis=1) / df['ma10']
    
    # 5日均量
    df['v_ma5'] = df['volume'].rolling(5).mean()
    return df

def check_pro_logic(df):
    if len(df) < 60: return None
    curr = df.iloc[-1]
    prev = df.iloc[-2]
    
    # --- 1. 寻找强势股基因 (前10天内有过突破) ---
    # 包含：连续涨停、跳空缺口、大阳突破
    recent_10 = df.tail(10)
    has_gap = (recent_10['low'] > recent_10['high'].shift(1)).any() # 跳空缺口
    has_big_yang = (recent_10['涨跌幅'] > 7).any() # 大阳线
    
    # 均线粘合向上发散判断
    is_ma_fanning = curr['ma5'] > curr['ma10'] > curr['ma20'] and prev['ma_std'] < 0.02

    if not (has_gap or has_big_yang or is_ma_fanning):
        return None

    # --- 2. 线上阴线买逻辑 (回踩支撑) ---
    signals = []
    is_yin = curr['close'] < curr['open'] or curr['涨跌幅'] < 0
    
    # 股价迅速腾空脱离5日线后回踩 (最高价偏离过ma5 > 5%)
    has_jumped = (df['high'].tail(5) > df['ma5'].tail(5) * 1.05).any()
    
    # 回踩10日线支撑 (允许1%误差，越近越好)
    on_ma10 = curr['low'] <= curr['ma10'] * 1.01 and curr['close'] >= curr['ma10'] * 0.98
    
    # 缩量洗盘判断 (成交量 < 5日均量)
    is_shrink = curr['volume'] < curr['v_ma5']

    if has_jumped and on_ma10 and is_yin and is_shrink:
        signals.append("线上阴线买(10日线)")
    elif has_jumped and curr['low'] <= curr['ma5'] * 1.005 and is_shrink:
        signals.append("线上阴线买(5日线)")

    return "+".join(signals) if signals else None

def main():
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    name_map = {}
    if os.path.exists(NAMES_FILE):
        try:
            name_df = pd.read_csv(NAMES_FILE, dtype={'code': str})
            name_map = dict(zip(name_df['code'], name_df['name']))
        except: pass

    files = glob.glob(f"{DATA_DIR}/*.csv")
    date_str = datetime.now().strftime('%Y-%m-%d')
    results = []

    for f in files:
        try:
            df = pd.read_csv(f)
            df.columns = [c.strip() for c in df.columns]
            # 自动映射不同券商导出的列名
            df = df.rename(columns={'收盘': 'close', '开盘': 'open', '最高': 'high', '最低': 'low', '成交量': 'volume'})
            
            df = get_indicators(df)
            match = check_pro_logic(df)
            
            if match:
                code = os.path.basename(f).replace('.csv', '')
                results.append({
                    '代码': code,
                    '名称': name_map.get(code, '未知'),
                    '当前价': round(df['close'].iloc[-1], 2),
                    '支撑位(MA10)': round(df['ma10'].iloc[-1], 2),
                    '形态类型': match,
                    '偏离度': f"{round((df['close'].iloc[-1]-df['ma10'].iloc[-1])/df['ma10'].iloc[-1]*100, 2)}%"
                })
        except: continue

    if results:
        pd.DataFrame(results).to_csv(f"{OUTPUT_DIR}/yin_pro_{date_str}.csv", index=False, encoding='utf-8-sig')
        print(f"✅ 找到 {len(results)} 只符合回踩逻辑的强势股")

if __name__ == "__main__":
    main()
