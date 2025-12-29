import pandas as pd
import numpy as np
import os
from datetime import datetime

# --- 配置 ---
DATA_DIR = 'stock_data'
OUTPUT_DIR = 'results/yin_line_strategy'

class YinLineStrategy:
    """基于上传图片的阴线买入战法"""
    
    @staticmethod
    def prepare_indicators(df):
        df = df.copy()
        # 核心均线
        for m in [5, 10, 20, 60]:
            df[f'ma{m}'] = df['close'].rolling(m).mean()
        # 5日平均成交量
        df['v_ma5'] = df['volume'].rolling(5).mean()
        return df

    @staticmethod
    def is_uptrend(df):
        """原则一：趋势为王，股价必须在60日线之上且60日线向上"""
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        return curr['close'] > curr['ma60'] and curr['ma60'] > prev['ma60']

    @staticmethod
    def logic_shrink_volume(df):
        """第一种：缩量回调阴线"""
        curr = df.iloc[-1]
        # 条件：阴线且收盘在5/10日线上，成交量小于5日均量50%
        is_yin = curr['close'] < curr['open']
        is_above_ma = curr['close'] > curr['ma5'] and curr['close'] > curr['ma10']
        is_shrink = curr['volume'] < (df.iloc[-6:-1]['volume'].mean() * 0.5)
        return is_yin and is_above_ma and is_shrink

    @staticmethod
    def logic_ma_touch(df):
        """第二种：回踩均线阴线"""
        curr = df.iloc[-1]
        is_yin = curr['close'] < curr['open']
        # 接近均线（1%范围内）且未跌破
        touch = False
        for m in [5, 10, 20, 60]:
            ma_val = curr[f'ma{m}']
            if 0 <= (curr['close'] - ma_val) / ma_val <= 0.01:
                touch = True
                break
        return is_yin and touch

    @staticmethod
    def logic_fake_yin(df):
        """第三种：放量假阴线（主力洗盘）"""
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        # 条件：阴线，但开盘价高于前收，收盘接近最高价
        is_yin = curr['close'] < curr['open']
        is_higher_open = curr['open'] > prev['close']
        is_near_high = (curr['high'] - curr['close']) / curr['close'] < 0.005
        # 成交量放大到前一天的1.5倍以上
        is_vol_burst = curr['volume'] > prev['volume'] * 1.5
        return is_yin and is_higher_open and is_near_high and is_vol_burst

def run_strategy():
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
    results = []
    
    for f in os.listdir(DATA_DIR):
        if not f.endswith('.csv'): continue
        try:
            df = pd.read_csv(os.path.join(DATA_DIR, f))
            if len(df) < 60: continue
            
            # 基础过滤：成交额 > 1亿 (避坑指南第2条)
            if (df['close'].iloc[-1] * df['volume'].iloc[-1]) < 100000000: continue
            
            df = YinLineStrategy.prepare_indicators(df)
            if not YinLineStrategy.is_uptrend(df): continue
            
            code = f.replace('.csv', '')
            match = []
            if YinLineStrategy.logic_shrink_volume(df): match.append("缩量回调")
            if YinLineStrategy.logic_ma_touch(df): match.append("回踩均线")
            if YinLineStrategy.logic_fake_yin(df): match.append("放量假阴线")
            
            if match:
                results.append({
                    'code': code,
                    'type': "+".join(match),
                    'price': df['close'].iloc[-1],
                    'date': datetime.now().strftime('%Y-%m-%d')
                })
        except: continue

    res_df = pd.DataFrame(results)
    if not res_df.empty:
        res_df.to_csv(f"{OUTPUT_DIR}/yin_signals_{datetime.now().strftime('%Y-%m-%d')}.csv", index=False, encoding='utf-8-sig')
        print(f"成功筛选出 {len(res_df)} 个阴线买入信号")

if __name__ == "__main__":
    run_strategy()
