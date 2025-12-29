import pandas as pd
import numpy as np
import os
from datetime import datetime

# --- 配置 ---
DATA_DIR = 'stock_data'
OUTPUT_DIR = 'results/yin_line_strategy'

class YinLineStrategy:
    """严格执行图片逻辑的阴线买入战法 - 增强诊断版"""
    
    # 用于统计过滤原因
    stats = {
        "total": 0,
        "fail_trend": 0,    # 趋势不达标
        "fail_amount": 0,   # 成交额不足
        "fail_logic": 0,    # 不符合三种形态
        "success": 0
    }

    @staticmethod
    def prepare_indicators(df):
        df = df.copy()
        for m in [5, 10, 20, 60]:
            df[f'ma{m}'] = df['close'].rolling(m).mean()
        # 5日平均成交量
        df['v_ma5_avg'] = df['volume'].shift(1).rolling(5).mean()
        return df

    @classmethod
    def check_rules(cls, df):
        cls.stats["total"] += 1
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        
        # 1. 基础准则：趋势 (股价在60日线上)
        # 修正：去掉了 ma60 > prev_ma60 的强行限制，改为股价在60线上且20日线向上
        if not (curr['close'] > curr['ma60'] and curr['ma20'] >= prev['ma20']):
            cls.stats["fail_trend"] += 1
            return None

        # 2. 避坑指南：日成交额 > 1亿 (请确保volume单位是'股'，如果是'手'需 *100)
        amount = curr['close'] * curr['volume']
        if amount < 100000000:
            cls.stats["fail_amount"] += 1
            return None

        is_yin = curr['close'] < curr['open']
        signals = []

        # --- 形态 1：缩量回调阴线 ---
        # 修正：缩量系数从 0.5 放宽到 0.7 (50%缩量在A股极罕见)
        if is_yin and curr['close'] > curr['ma5'] and curr['close'] > curr['ma10']:
            if curr['volume'] < (curr['v_ma5_avg'] * 0.7):
                signals.append("缩量回调")

        # --- 形态 2：回踩均线阴线 ---
        if is_yin:
            for m in [5, 10, 20]:
                if curr[f'ma{m}'] >= prev[f'ma{m}']: # 均线走平或向上
                    # 触碰均线：最低价低于均线，收盘价高于均线（回踩不破）
                    if curr['low'] <= curr[f'ma{m}'] and curr['close'] >= curr[f'ma{m}']:
                        signals.append(f"回踩MA{m}")
                        break

        # --- 形态 3：放量假阴线 ---
        # 条件：收阳线实体的“假阴线”（收盘 > 前收，但收盘 < 开盘）
        if is_yin and curr['close'] > prev['close']:
            if curr['volume'] > (prev['volume'] * 1.3): # 放量1.3倍
                # 上影线不要太长
                if (curr['high'] - max(curr['open'], curr['close'])) / curr['close'] < 0.03:
                    signals.append("放量假阴线")

        if signals:
            cls.stats["success"] += 1
            return "+".join(signals)
        else:
            cls.stats["fail_logic"] += 1
            return None

def run_strategy():
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
    results = []
    
    if not os.path.exists(DATA_DIR):
        print(f"❌ 错误：找不到目录 {DATA_DIR}")
        return

    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
    print(f"📂 正在扫描 {len(files)} 个标的...")

    for f in files:
        try:
            df = pd.read_csv(os.path.join(DATA_DIR, f))
            if len(df) < 60: continue
            
            df = YinLineStrategy.prepare_indicators(df)
            match_type = YinLineStrategy.check_rules(df)
            
            if match_type:
                results.append({
                    '代码': f.replace('.csv', ''),
                    '形态类型': match_type,
                    '收盘价': round(df['close'].iloc[-1], 2),
                    '成交额(亿)': round((df['close'].iloc[-1] * df['volume'].iloc[-1])/100000000, 2),
                    '日期': datetime.now().strftime('%Y-%m-%d')
                })
        except Exception as e:
            continue

    # 打印诊断报告
    print("\n" + "="*30)
    print("📊 策略扫描诊断报告")
    print(f"总扫描数: {YinLineStrategy.stats['total']}")
    print(f"趋势不符: {YinLineStrategy.stats['fail_trend']} (股价需在MA60上)")
    print(f"金额不足: {YinLineStrategy.stats['fail_amount']} (成交额需>1亿)")
    print(f"逻辑不符: {YinLineStrategy.stats['fail_logic']} (非指定阴线形态)")
    print(f"最终入选: {YinLineStrategy.stats['success']}")
    print("="*30 + "\n")

    if results:
        res_df = pd.DataFrame(results)
        file_path = f"{OUTPUT_DIR}/yin_signals_{datetime.now().strftime('%Y-%m-%d')}.csv"
        res_df.to_csv(file_path, index=False, encoding='utf-8-sig')
        print(f"🔥 发现 {len(res_df)} 个目标，结果已保存至: {file_path}")
    else:
        print("❄️ 本次扫描未发现符合条件的信号")

if __name__ == "__main__":
    run_strategy()
