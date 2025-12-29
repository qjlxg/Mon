import pandas as pd
import os
import glob
from datetime import datetime
from multiprocessing import Pool, cpu_count
import re

# 配置常量
DATA_DIR = 'stock_data'
NAMES_FILE = 'stock_names.csv'
OUTPUT_BASE = 'results'

def analyze_logic(file_path):
    try:
        # 1. 基础数据加载
        df = pd.read_csv(file_path)
        if len(df) < 30: return None
        
        # 字段映射（处理中文表头）
        df = df.rename(columns={
            '日期': 'date',
            '股票代码': 'code',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume'
        })
        
        # 获取股票代码并补齐6位
        code_raw = str(df.iloc[-1]['code']).split('.')[0]
        code = code_raw.zfill(6)
        
        # 只要沪深A股 (60, 00开头)，排除30(创业板)
        if not (code.startswith('60') or code.startswith('00')):
            return None

        # 2. 价格过滤: 5.0 - 20.0 元
        curr_close = df.iloc[-1]['close']
        if not (5.0 <= curr_close <= 20.0):
            return None

        # 3. 计算技术指标
        df['ma5'] = df['close'].rolling(window=5).mean()
        df['ma10'] = df['close'].rolling(window=10).mean()
        df['vol_ma5'] = df['volume'].rolling(window=5).mean()
        
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        
        # --- 核心筛选逻辑 (老鸭头变异版) ---
        
        # A. 股价在5, 10日线之上，且5日线在10日线之上 (多头排列形态)
        cond_a = curr['close'] > curr['ma5'] and curr['close'] > curr['ma10'] and curr['ma5'] > curr['ma10']
        
        # B. 均线向上 (ma5 > prev_ma5)
        cond_b = curr['ma5'] > prev['ma5']
        
        # C. 量比：当前成交量大于5日均量的1.2倍 (放量) 
        #    或者：处于回踩不破MA10 (缩量回踩支撑)
        cond_vol_surge = curr['volume'] > curr['vol_ma5'] * 1.2
        cond_backtest_support = curr['close'] >= curr['ma10'] and curr['volume'] <= curr['vol_ma5']
        
        cond_c = cond_vol_surge or cond_backtest_support

        if cond_a and cond_b and cond_c:
            return {'code': code, 'price': round(curr_close, 2)}
            
    except Exception:
        return None
    return None

def main():
    # 检查名称文件并排除ST (修复了正则表达式错误)
    if not os.path.exists(NAMES_FILE):
        return
    
    names_df = pd.read_csv(NAMES_FILE, dtype={'code': str})
    # 使用 \* 转义星号，或者直接匹配 ST (ST 已经包含了 *ST)
    names_df = names_df[~names_df['name'].str.contains(r'ST|退|\*ST', na=False)]
    valid_codes = set(names_df['code'].apply(lambda x: x.zfill(6)).tolist())

    # 扫描目录下所有符合条件的CSV
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)
        
    files = [f for f in glob.glob(f'{DATA_DIR}/*.csv') if os.path.basename(f).split('.')[0].zfill(6) in valid_codes]
    
    if not files:
        print("No data files to process.")
        return

    # 并行处理
    with Pool(cpu_count()) as p:
        results = p.map(analyze_logic, files)
    
    results = [r for r in results if r is not None]
    
    if results:
        res_df = pd.DataFrame(results)
        final_df = pd.merge(res_df, names_df, on='code', how='left')
        
        now = datetime.now()
        dir_path = os.path.join(OUTPUT_BASE, now.strftime('%Y%m'))
        os.makedirs(dir_path, exist_ok=True)
        
        timestamp = now.strftime('%Y%m%d_%H%M%S')
        save_path = os.path.join(dir_path, f"duck_hunter_{timestamp}.csv")
        
        final_df[['code', 'name', 'price']].to_csv(save_path, index=False)
        print(f"Filter complete. Found {len(final_df)} stocks.")
    else:
        print("No stocks matched the criteria.")

if __name__ == "__main__":
    main()
