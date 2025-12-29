import pandas as pd
import os
import glob
from datetime import datetime
from multiprocessing import Pool, cpu_count

DATA_DIR = 'stock_data'
NAMES_FILE = 'stock_names.csv'
OUTPUT_BASE = 'results/golden_pit'

def analyze_logic(file_path):
    try:
        df = pd.read_csv(file_path)
        if len(df) < 40: return None
        df = df.rename(columns={'日期':'date','股票代码':'code','开盘':'open','收盘':'close','成交量':'volume','最低':'low'})
        
        recent = df.iloc[-20:] # 观察过去20天
        curr = df.iloc[-1]
        
        pit_low = recent['low'].min()
        avg_vol = df['volume'].rolling(20).mean().iloc[-1]

        # 核心：坑底反弹5%-12%之间，今日收阳线，且成交量开始温和放大
        cond_rebound = (curr['close'] > pit_low * 1.05) and (curr['close'] < pit_low * 1.15)
        cond_sun = curr['close'] > curr['open']
        cond_vol = curr['volume'] > avg_vol * 0.8 # 摆脱地量
        
        if cond_rebound and cond_sun and cond_vol:
            return {
                'date': curr['date'],
                'code': str(curr['code']).split('.')[0].zfill(6),
                'price': curr['close'],
                'rebound': f"{round((curr['close']/pit_low-1)*100, 2)}%"
            }
    except: return None

def main():
    if not os.path.exists(NAMES_FILE): return
    os.makedirs(OUTPUT_BASE, exist_ok=True)
    files = glob.glob(f'{DATA_DIR}/*.csv')
    with Pool(cpu_count()) as p:
        results = [r for r in p.map(analyze_logic, files) if r is not None]
    if results:
        res_df = pd.DataFrame(results)
        names = pd.read_csv(NAMES_FILE, dtype={'code': str})
        names['code'] = names['code'].apply(lambda x: x.zfill(6))
        res_df = pd.merge(res_df, names, on='code', how='left')
        save_path = f"{OUTPUT_BASE}/golden_pit_{datetime.now().strftime('%Y%m%d')}.csv"
        res_df.to_csv(save_path, index=False)
        print(f"黄金坑发现: {len(res_df)} 只")

if __name__ == "__main__":
    main()
