import pandas as pd
import numpy as np
import os
from datetime import datetime

# --- 配置 ---
DATA_DIR = 'stock_data'
OUTPUT_DIR = 'results/yin_line_strategy'

class YinLineStrategy:
    """完美对齐图片逻辑：极致精选版"""
    
    stats = {"total": 0, "fail_trend": 0, "fail_amount": 0, "fail_logic": 0, "success": 0}

    @staticmethod
    def prepare_indicators(df):
        # 匹配截图中的表头
        column_map = {'开盘': 'open', '收盘': 'close', '最高': 'high', '最低': 'low', '成交量': 'volume', '成交额': 'amount'}
        df = df.rename(columns=column_map)
        required = ['open', 'close', 'high', 'low', 'volume', 'amount']
        if not all(col in df.columns for col in required): return None

        df = df.copy()
        for col in required: df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 计算均线
        for m in [5, 10, 20, 60]:
            df[f'ma{m}'] = df['close'].rolling(m).mean()
            
        # 5日平均成交量 (用于严格缩量判断)
        df['v_ma5_avg'] = df['volume'].shift(1).rolling(5).mean()
        return df

    @classmethod
    def check_rules(cls, df):
        if len(df) < 60: return None
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        
        # --- 原则一：趋势为王 ---
        # 股价在60日线上，且60日线必须向上走
        if not (curr['close'] > curr['ma60'] and curr['ma60'] > prev['ma60']):
            cls.stats["fail_trend"] += 1
            return None

        # --- 避坑指南：成交额 > 1亿 ---
        if curr['amount'] < 100000000:
            cls.stats["fail_amount"] += 1
            return None

        cls.stats["total"] += 1
        is_yin = curr['close'] < curr['open']
        signals = []

        # 1. 缩量回调阴线 (硬指标：缩量至50%以下)
        if is_yin and curr['close'] > curr['ma5'] and curr['close'] > curr['ma10']:
            if curr['volume'] < (curr['v_ma5_avg'] * 0.5):
                signals.append("极致缩量回调")

        # 2. 回踩均线阴线 (要求均线向上，且收盘不破)
        if is_yin:
            for m in [5, 10, 20]:
                if curr[f'ma{m}'] > prev[f'ma{m}']: # 均线向上
                    if curr['low'] <= curr[f'ma{m}'] and curr['close'] >= curr[f'ma{m}']:
                        signals.append(f"回踩MA{m}")
                        break

        # 3. 放量假阴线 (洗盘陷阱)
        # 条件：当天阴线，但开盘 > 前收，且收盘接近最高价，成交量放大1.5倍
        if is_yin and curr['open'] > prev['close']:
            vol_ratio = curr['volume'] / prev['volume']
            high_limit = (curr['high'] - curr['close']) / curr['close'] 
            if vol_ratio > 1.5 and high_limit < 0.01: # 接近最高价收盘
                signals.append("放量假阴洗盘")

        if signals:
            cls.stats["success"] += 1
            return "+".join(signals)
        
        cls.stats["fail_logic"] += 1
        return None

def run_strategy():
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
    results = []
    
    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
    print(f"📂 正在执行图片战法逻辑，扫描 {len(files)} 个文件...")

    for f in files:
        try:
            file_path = os.path.join(DATA_DIR, f)
            # 兼容编码
            try: df = pd.read_csv(file_path, encoding='utf-8')
            except: df = pd.read_csv(file_path, encoding='gbk')
                
            df = YinLineStrategy.prepare_indicators(df)
            if df is None: continue
            
            match_type = YinLineStrategy.check_rules(df)
            if match_type:
                results.append({
                    '代码': f.replace('.csv', ''),
                    '符合战法': match_type,
                    '收盘': curr_close := round(df['close'].iloc[-1], 2),
                    '成交额(亿)': round(df['amount'].iloc[-1] / 100000000, 2),
                    'MA60斜率': "向上" if df['ma60'].iloc[-1] > df['ma60'].iloc[-2] else "平缓",
                    '建议': "分批买入/设止损线"
                })
        except: continue

    print("\n" + "="*30)
    print(f"📊 图片战法诊断报告")
    print(f"符合60日线趋势: {YinLineStrategy.stats['total']}")
    print(f" └─ 缩量/回踩/假阴匹配成功: {YinLineStrategy.stats['success']}")
    print(f" └─ 虽在趋势中但形态不佳: {YinLineStrategy.stats['fail_logic']}")
    print("="*30 + "\n")

    if results:
        res_df = pd.DataFrame(results)
        # 按成交额降序排列，优先看活跃股
        res_df = res_df.sort_values(by='成交额(亿)', ascending=False)
        save_path = f"{OUTPUT_DIR}/final_yin_strategy.csv"
        res_df.to_csv(save_path, index=False, encoding='utf-8-sig')
        print(f"✅ 筛选完成！最终入选 {len(res_df)} 个精选标的。")
    else:
        print("❄️ 未发现完全符合图片逻辑的极致信号")

if __name__ == "__main__":
    run_strategy()
