import pandas as pd
import os
import glob
from datetime import datetime

# --- 配置区 ---
DATA_DIR = 'stock_data'
NAMES_FILE = 'stock_names.csv'
# 16个战法的输出目录映射
STRATEGY_MAP = {
    'macd_bottom': 'results/macd_bottom',          # 1. MACD抄底
    'duck_head': 'results/duck_head',              # 2. 老鸭头
    'three_in_one': 'results/three_in_one',        # 3. 三位一体
    'pregnancy_line': 'results/pregnancy_line',    # 4. 底部孕线
    'single_yang': 'results/single_yang',          # 5. 单阳不破
    'limit_pullback': 'results/limit_pullback',    # 6. 涨停回调
    'golden_pit': 'results/golden_pit',            # 7. 黄金坑
    'grass_fly': 'results/grass_fly',              # 8. 草上飞
    'limit_break': 'results/limit_break',          # 9. 涨停破位
    'double_plate': 'results/double_plate',        # 10. 阴阳双板
    'horse_back': 'results/horse_back',            # 11. 洗盘回马枪
    'hot_money': 'results/hot_money',              # 12. 游资回调
    'wave_bottom': 'results/wave_bottom',          # 13. 波动抄底
    'no_loss': 'results/no_loss',                  # 14. 牛散不亏钱
    'chase_rise': 'results/chase_rise',            # 15. 高手追涨
    'inst_swing': 'results/inst_swing'             # 16. 机构波段
}

class AlphaLogics:
    """根据16张图片完善的量化逻辑"""
    
    @staticmethod
    def get_indicators(df):
        # 计算均线
        for m in [5, 10, 20, 34, 60, 120, 250]:
            df[f'ma{m}'] = df['close'].rolling(m).mean()
        # 计算MACD
        df['ema12'] = df['close'].ewm(span=12).mean()
        df['ema26'] = df['close'].ewm(span=26).mean()
        df['diff'] = df['ema12'] - df['ema26']
        df['dea'] = df['diff'].ewm(span=9).mean()
        df['macd'] = (df['diff'] - df['dea']) * 2
        return df

    # --- 16个独立逻辑函数 ---
    @staticmethod
    def logic_macd_bottom(df):
        return df['diff'].iloc[-1] < 0 and df['diff'].iloc[-2] < df['dea'].iloc[-2] and df['diff'].iloc[-1] > df['dea'].iloc[-1]

    @staticmethod
    def logic_duck_head(df):
        return df['ma5'].iloc[-1] > df['ma10'].iloc[-1] and df['low'].iloc[-1] <= df['ma20'].iloc[-1] * 1.01

    @staticmethod
    def logic_three_in_one(df):
        # 巨阳(>5%) + 放量(>2倍) + 60日线上
        return (df['close'].iloc[-1]/df['close'].iloc[-2] > 1.05) and (df['volume'].iloc[-1] > df['volume'].rolling(5).mean().iloc[-1] * 2) and (df['close'].iloc[-1] > df['ma60'].iloc[-1])

    @staticmethod
    def logic_pregnancy_line(df):
        return df['high'].iloc[-1] < df['high'].iloc[-2] and df['low'].iloc[-1] > df['low'].iloc[-2]

    @staticmethod
    def logic_single_yang(df):
        yang_idx = -7
        return (df['close'].iloc[yang_idx]/df['close'].iloc[yang_idx-1] > 1.05) and (df['low'].iloc[yang_idx+1:].min() >= df['low'].iloc[yang_idx])

    @staticmethod
    def logic_limit_pullback(df):
        return (df['close'].iloc[-5]/df['close'].iloc[-6] > 1.095) and (df['volume'].iloc[-1] < df['volume'].rolling(5).mean().iloc[-1])

    @staticmethod
    def logic_golden_pit(df):
        return df['ma5'].iloc[-3] < df['ma34'].iloc[-3] and df['ma5'].iloc[-1] > df['ma34'].iloc[-1]

    @staticmethod
    def logic_grass_fly(df):
        return abs(df['close'].iloc[-1] - df['ma60'].iloc[-1]) / df['ma60'].iloc[-1] < 0.015

    @staticmethod
    def logic_limit_break(df):
        return (df['close'].iloc[-4]/df['close'].iloc[-5] > 1.095) and (df['close'].iloc[-1] > df['close'].iloc[-4])

    @staticmethod
    def logic_double_plate(df):
        return (df['close'].iloc[-3]/df['close'].iloc[-4] > 1.095) and (df['close'].iloc[-2] < df['open'].iloc[-2]) and (df['close'].iloc[-1] > df['open'].iloc[-1])

    @staticmethod
    def logic_horse_back(df):
        return (df['close'].iloc[-2]/df['close'].iloc[-3] > 1.095) and (df['low'].iloc[-1] <= df['ma5'].iloc[-1])

    @staticmethod
    def logic_hot_money(df):
        return df['volume'].iloc[-1] > df['volume'].iloc[-2] * 2.5 and df['close'].iloc[-1] > df['open'].iloc[-1]

    @staticmethod
    def logic_wave_bottom(df):
        return df['close'].iloc[-1] > df['ma5'].iloc[-1] and df['close'].iloc[-1] < df['ma20'].iloc[-1]

    @staticmethod
    def logic_no_loss(df):
        return df['close'].iloc[-1] > df['ma250'].iloc[-1]

    @staticmethod
    def logic_chase_rise(df):
        return df['close'].iloc[-1] > df['high'].iloc[-20:-1].max()

    @staticmethod
    def logic_inst_swing(df):
        return df['macd'].iloc[-1] > df['macd'].iloc[-2] > 0

def run_all_strategies():
    # 获取股票名称映射
    name_map = {}
    if os.path.exists(NAMES_FILE):
        name_df = pd.read_csv(NAMES_FILE, dtype={'code': str})
        name_map = dict(zip(name_df['code'], name_df['name']))

    files = glob.glob(f"{DATA_DIR}/*.csv")
    date_str = datetime.now().strftime('%Y-%m-%d')
    all_results = {k: [] for k in STRATEGY_MAP.keys()}

    for f in files:
        try:
            df = pd.read_csv(f)
            if len(df) < 250: continue # 确保年线计算
            df = df.rename(columns={'日期':'date','股票代码':'code','开盘':'open','收盘':'close','成交量':'volume','涨跌幅':'pct_chg','换手率':'turnover'})
            code = os.path.basename(f).replace('.csv','')
            
            # 基础过滤：5-35元
            if not (5.0 <= df['close'].iloc[-1] <= 35.0): continue
            
            df = AlphaLogics.get_indicators(df)
            
            # 运行16个逻辑
            for s_key in STRATEGY_MAP.keys():
                logic_func = getattr(AlphaLogics, f"logic_{s_key}")
                if logic_func(df):
                    all_results[s_key].append({
                        'date': date_str,
                        'code': code,
                        'name': name_map.get(code, '未知'),
                        'price': df['close'].iloc[-1]
                    })
        except: continue

    # 保存结果
    for s_key, path in STRATEGY_MAP.items():
        if not os.path.exists(path): os.makedirs(path, exist_ok=True)
        res_df = pd.DataFrame(all_results[s_key])
        res_df.to_csv(f"{path}/{s_key}_{date_str}.csv", index=False, encoding='utf-8-sig')
        print(f"战法 {s_key} 完成，发现 {len(res_df)} 个目标")

if __name__ == "__main__":
    run_all_strategies()
