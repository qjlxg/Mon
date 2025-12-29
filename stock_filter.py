import pandas as pd
import os
import glob
from datetime import datetime
from multiprocessing import Pool, cpu_count

# 配置常量
DATA_DIR = 'stock_data'
NAMES_FILE = 'stock_names.csv'
OUTPUT_BASE = 'results'

def analyze_stock(file_path):
    try:
        df = pd.read_csv(file_path)
        if len(df) < 30: return None
        
        # 基础信息获取
        code = os.path.basename(file_path).split('.')[0]
        
        # 1. 排除特定板块：只要沪深A股 (60, 00开头)，排除30(创业板), 68(科创板), ST由外部逻辑或名称判断
        if not (code.startswith('60') or code.startswith('00')):
            return None

        last_row = df.iloc[-1]
        close = last_row['close']
        
        # 2. 价格过滤: 5.0 - 20.0
        if not (5.0 <= close <= 20.0):
            return None

        # 3. 技术指标计算 (简单实现图片中的逻辑)
        df['ma5'] = df['close'].rolling(window=5).mean()
        df['ma10'] = df['close'].rolling(window=10).mean()
        df['vol_ma5'] = df['volume'].rolling(window=5).mean()
        
        curr_close = df['close'].iloc[-1]
        prev_close = df['close'].iloc[-2]
        curr_ma5 = df['ma5'].iloc[-1]
        curr_ma10 = df['ma10'].iloc[-1]
        curr_vol = df['volume'].iloc[-1]
        avg_vol = df['vol_ma5'].iloc[-2] # 前5日平均量

        # 筛选逻辑：
        # A. 股价在5, 10日线之上 (多头排列)
        # B. 均线向上 (ma5 > prev_ma5)
        # C. 量比：当前成交量大于5日均量的1.2倍 (放量) 或 处于回踩不破MA10
        condition_trend = curr_close > curr_ma5 > curr_ma10
        condition_volume = curr_vol > avg_vol * 1.2
        
        if condition_trend and condition_volume:
            return {'code': code, 'price': curr_close}
    except:
        return None
    return None

def main():
    # 加载股票名称
    names_df = pd.read_csv(NAMES_FILE, dtype={'code': str})
    # 排除ST
    names_df = names_df[~names_df['name'].str.contains('ST|退')]
    valid_codes = set(names_df['code'].tolist())

    files = [f for f in glob.glob(f'{DATA_DIR}/*.csv') if os.path.basename(f).split('.')[0] in valid_codes]
    
    # 并行处理
    with Pool(cpu_count()) as p:
        results = p.map(analyze_stock, files)
    
    results = [r for r in results if r is not None]
    
    if results:
        res_df = pd.DataFrame(results)
        # 匹配名称
        final_df = pd.merge(res_df, names_df, on='code', how='left')
        
        # 结果保存路径
        now = datetime.now()
        dir_path = os.path.join(OUTPUT_BASE, now.strftime('%Y%m'))
        os.makedirs(dir_path, exist_ok=True)
        
        file_name = f"select_{now.strftime('%Y%m%d_%H%M%S')}.csv"
        final_df[['code', 'name', 'price']].to_csv(os.path.join(dir_path, file_name), index=False)
        print(f"筛选完成，找到 {len(final_df)} 只股票。")

if __name__ == "__main__":
    main()
