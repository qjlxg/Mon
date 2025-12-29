import pandas as pd
import numpy as np
import os
from datetime import datetime

# --- 配置 ---
DATA_DIR = 'stock_data'
OUTPUT_DIR = 'results/yin_line_strategy'

class YinLineStrategy:
    """针对特定中文格式优化的阴线战法"""
    
    stats = {"total": 0, "fail_trend": 0, "fail_amount": 0, "fail_logic": 0, "success": 0}

    @staticmethod
    def prepare_indicators(df):
        # 1. 映射你的截图表头
        column_map = {
            '开盘': 'open', '收盘': 'close', 
            '最高': 'high', '最低': 'low', 
            '成交量': 'volume', '成交额': 'amount'
        }
        df = df.rename(columns=column_map)
        
        # 2. 检查必要列
        required = ['open', 'close', 'high', 'low', 'volume', 'amount']
        if not all(col in df.columns for col in required):
            return None

        df = df.copy()
        # 转换为数值型，防止字符串干扰
        for col in required:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 3. 计算均线
        for m in [5, 10, 20, 60]:
            df[f'ma{m}'] = df['close'].rolling(m).mean()
            
        # 5日平均成交量 (用于判断缩量)
        df['v_ma5_avg'] = df['volume'].shift(1).rolling(5).mean()
        return df

    @classmethod
    def check_rules(cls, df):
        if len(df) < 60: return None
        
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        
        # --- 过滤条件 ---
        
        # 1. 趋势：股价在60日线上
        if not (curr['close'] > curr['ma60']):
            cls.stats["fail_trend"] += 1
            return None

        # 2. 成交额：大于1亿 (根据截图，成交额列似乎是以'元'为单位)
        if curr['amount'] < 100000000:
            cls.stats["fail_amount"] += 1
            return None

        cls.stats["total"] += 1
        is_yin = curr['close'] < curr['open'] # 阴线定义
        signals = []

        # --- 三大逻辑 ---

        # 逻辑1：缩量回调 (成交量 < 5日均量的70%)
        if is_yin and curr['close'] > curr['ma5'] and curr['volume'] < (curr['v_ma5_avg'] * 0.7):
            signals.append("缩量回调")

        # 逻辑2：回踩均线 (MA5/10/20)
        if is_yin:
            for m in [5, 10, 20]:
                # 触碰均线且收盘守住
                if curr['low'] <= curr[f'ma{m}'] and curr['close'] >= curr[f'ma{m}']:
                    if curr[f'ma{m}'] >= prev[f'ma{m}']: # 均线不下降
                        signals.append(f"回踩MA{m}")
                        break

        # 逻辑3：放量假阴线 (收盘 > 前收，但当天是阴线，且放量)
        if is_yin and curr['close'] > prev['close']:
            if curr['volume'] > (prev['volume'] * 1.3):
                signals.append("放量假阴线")

        if signals:
            cls.stats["success"] += 1
            return "+".join(signals)
        
        cls.stats["fail_logic"] += 1
        return None

def run_strategy():
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
    results = []
    
    if not os.path.exists(DATA_DIR):
        print(f"❌ 找不到目录: {DATA_DIR}")
        return

    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
    print(f"📂 正在分析 {len(files)} 个文件...")

    for f in files:
        try:
            # 增加 encoding='utf-8' 或 'gbk' 兼容性处理
            file_path = os.path.join(DATA_DIR, f)
            try:
                df = pd.read_csv(file_path, encoding='utf-8')
            except:
                df = pd.read_csv(file_path, encoding='gbk')
                
            df = YinLineStrategy.prepare_indicators(df)
            if df is None: continue
            
            match_type = YinLineStrategy.check_rules(df)
            if match_type:
                results.append({
                    '代码': f.replace('.csv', ''),
                    '形态': match_type,
                    '现价': round(df['close'].iloc[-1], 2),
                    '成交额(亿)': round(df['amount'].iloc[-1] / 100000000, 2),
                    '日期': datetime.now().strftime('%Y-%m-%d')
                })
        except Exception as e:
            continue

    # 输出诊断
    print("\n" + "="*30)
    print(f"📊 策略扫描报告 ({datetime.now().strftime('%Y-%m-%d')})")
    print(f"总处理文件: {len(files)}")
    print(f"通过基础过滤: {YinLineStrategy.stats['total']}")
    print(f" └─ 趋势不符 (收盘<MA60): {YinLineStrategy.stats['fail_trend']}")
    print(f" └─ 成交额不足 (低于1亿): {YinLineStrategy.stats['fail_amount']}")
    print(f"符合战法信号: {YinLineStrategy.stats['success']}")
    print("="*30 + "\n")

    if results:
        res_df = pd.DataFrame(results)
        save_path = f"{OUTPUT_DIR}/yin_signals_{datetime.now().strftime('%Y-%m-%d')}.csv"
        res_df.to_csv(save_path, index=False, encoding='utf-8-sig')
        print(f"🔥 筛选完成！结果已存入: {save_path}")
    else:
        print("❄️ 今日未发现符合条件的阴线机会")

if __name__ == "__main__":
    run_strategy()
