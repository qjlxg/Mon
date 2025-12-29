import pandas as pd
import os
import glob
from datetime import datetime
from multiprocessing import Pool, cpu_count

# 配置常量
DATA_DIR = 'stock_data'
NAMES_FILE = 'stock_names.csv'
OUTPUT_BASE = 'results'

def analyze_logic(file_path):
    try:
        # 1. 基础数据加载与代码过滤
        df = pd.read_csv(file_path)
        if len(df) < 30: return None
        
        code = os.path.basename(file_path).split('.')[0]
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
        
        # 定义当前和前一日/前五日数据
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        
        # --- 您的核心筛选逻辑 ---
        
        # A. 股价在5, 10日线之上 (多头排列)
        cond_a = curr['close'] > curr['ma5'] and curr['ma5'] > curr['ma10']
        
        # B. 均线向上 (ma5 > prev_ma5) - 确保趋势斜率向上
        cond_b = curr['ma5'] > prev['ma5']
        
        # C. 量比逻辑：当前成交量 > 5日均量的1.2倍 (放量)
        # 或者：处于缩量回踩但收盘不破MA10
        cond_vol_surge = curr['volume'] > curr['vol_ma5'] * 1.2
        cond_backtest_support = curr['close'] >= curr['ma10'] and curr['volume'] <= curr['vol_ma5']
        
        cond_c = cond_vol_surge or cond_backtest_support

        # 综合判断
        if cond_a and cond_b and cond_c:
            return {'code': code, 'price': round(curr_close, 2)}
            
    except Exception:
        return None
    return None

def main():
    # 检查并加载名称文件 (排除ST)
    if not os.path.exists(NAMES_FILE):
        print(f"File {NAMES_FILE} not found.")
        return
    
    names_df = pd.read_csv(NAMES_FILE, dtype={'code': str})
    names_df = names_df[~names_df['name'].str.contains('ST|退|*ST')]
    valid_codes = set(names_df['code'].tolist())

    # 扫描目录下所有符合条件的CSV
    files = [f for f in glob.glob(f'{DATA_DIR}/*.csv') if os.path.basename(f).split('.')[0] in valid_codes]
    
    # 并行加速处理
    with Pool(cpu_count()) as p:
        results = p.map(analyze_logic, files)
    
    # 清洗结果并匹配名称
    results = [r for r in results if r is not None]
    
    if results:
        res_df = pd.DataFrame(results)
        final_df = pd.merge(res_df, names_df, on='code', how='left')
        
        # 创建年月目录
        now = datetime.now()
        dir_path = os.path.join(OUTPUT_BASE, now.strftime('%Y%m'))
        os.makedirs(dir_path, exist_ok=True)
        
        # 文件名：duck_hunter_时间戳.csv
        timestamp = now.strftime('%Y%m%d_%H%M%S')
        save_path = os.path.join(dir_path, f"duck_hunter_{timestamp}.csv")
        
        final_df[['code', 'name', 'price']].to_csv(save_path, index=False)
        print(f"Successfully filtered {len(final_df)} stocks to {save_path}")
    else:
        print("No stocks matched the criteria today.")

if __name__ == "__main__":
    main()
