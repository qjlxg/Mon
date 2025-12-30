import pandas as pd
import numpy as np
import os
import glob
from datetime import datetime

# --- 配置区 ---
DATA_DIR = 'stock_data'
OUTPUT_DIR = 'results/online_yin_final'
NAMES_FILE = 'stock_names.csv'

def get_indicators(df):
    df = df.copy()
    # 核心均线系统
    for m in [5, 10, 20, 60]:
        df[f'ma{m}'] = df['收盘'].rolling(m).mean()
    
    # 均线多头趋势判断
    df['ma10_up'] = df['ma10'] > df['ma10'].shift(1)
    df['ma60_up'] = df['ma60'] > df['ma60'].shift(1)
    
    # 成交量：5日均量
    df['v_ma5'] = df['成交量'].rolling(5).mean()
    df['vol_avg_10'] = df['成交量'].rolling(10).mean()
    
    # 涨跌幅
    df['change'] = df['收盘'].pct_change() * 100
    return df

def check_strict_logic(df):
    if len(df) < 60: return None
    curr = df.iloc[-1]
    prev = df.iloc[-2]

    # --- 条件1：价格过滤 (5元以上，20元以下) ---
    if not (5.0 <= curr['收盘'] <= 20.0):
        return None

    # --- 条件2：资金门槛 (成交额 > 3亿，确保热点) ---
    if curr['成交额'] < 300000000:
        return None

    # --- 条件3：强势基因 (15天内必须有涨停或9.5%以上大阳) ---
    recent_15 = df.tail(15)
    is_limit_up = (recent_15['change'] > 9.5).any()
    if not is_limit_up:
        return None

    # --- 条件4：线上阴线形态 ---
    # 必须是阴线（或收盘价低于开盘价/微跌），且在10日线上方
    is_yin = curr['收盘'] < curr['开盘'] or curr['change'] <= 0
    if not (is_yin and curr['收盘'] >= curr['ma10'] * 0.995):
        return None

    # --- 条件5：腾空回踩 (曾脱离5日线 > 7%) ---
    has_jumped = (df['最高'].tail(10) > df['ma5'].tail(10) * 1.07).any()
    
    # --- 条件6：缩量判定 (成交量 < 5日均量) ---
    is_shrink = curr['成交量'] < df['v_ma5'].iloc[-1]

    if has_jumped and is_shrink and curr['ma10_up'] and curr['收盘'] > curr['ma60']:
        # 额外：3倍量卖出预警逻辑
        if curr['成交量'] > curr['vol_avg_10'] * 3:
            return "3倍量卖出预警"
        return "线上阴线买(精选)"
    
    return None

def main():
    if not os.path.exists(OUTPUT_DIR): 
        os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    name_map = {}
    if os.path.exists(NAMES_FILE):
        try:
            n_df = pd.read_csv(NAMES_FILE, dtype={'code': str})
            name_map = dict(zip(n_df['code'], n_df['name']))
        except: pass

    files = glob.glob(f"{DATA_DIR}/*.csv")
    date_str = datetime.now().strftime('%Y-%m-%d')
    results = []

    for f in files:
        try:
            df = pd.read_csv(f)
            df.columns = [c.strip() for c in df.columns]
            # 兼容处理
            df = df.rename(columns={'收盘': 'close', '成交额': 'amount'}) 
            
            df = get_indicators(df)
            match = check_strict_logic(df)
            
            if match:
                code = os.path.basename(f).replace('.csv', '')
                curr_p = df['收盘'].iloc[-1]
                ma10_p = df['ma10'].iloc[-1]
                results.append({
                    '代码': code,
                    '名称': name_map.get(code, '未知'),
                    '当前价': round(curr_p, 2),
                    '10日线': round(ma10_p, 2),
                    '偏离度%': round((curr_p - ma10_p) / ma10_p * 100, 2),
                    '成交额(亿)': round(df['成交额'].iloc[-1] / 100000000, 2),
                    '形态': match
                })
        except: continue

    if results:
        res_df = pd.DataFrame(results)
        # 按偏离度绝对值排序（越贴合10日线越靠前）
        res_df['abs_bias'] = res_df['偏离度%'].abs()
        res_df = res_df.sort_values(by='abs_bias').drop(columns=['abs_bias'])
        res_df.to_csv(f"{OUTPUT_DIR}/final_yin_{date_str}.csv", index=False, encoding='utf-8-sig')
        print(f"🎯 扫描完成：符合[5-20元+3亿成交+强势回踩]的目标共 {len(results)} 个")
    else:
        print("今日未发现符合严苛条件的信号")

if __name__ == "__main__":
    main()
