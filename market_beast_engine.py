import pandas as pd
import numpy as np
import os
import glob
from datetime import datetime

# --- 基础配置保持不变 ---
DATA_DIR = 'stock_data'
NAMES_FILE = 'stock_names.csv'

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
    """根据16张图片完善的量化逻辑（加入实战容错）"""
    
    @staticmethod
    def get_indicators(df):
        df = df.copy()
        # 均线
        for m in [5, 10, 20, 34, 60, 120, 250]:
            df[f'ma{m}'] = df['close'].rolling(m).mean()
        # MACD
        df['ema12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['ema26'] = df['close'].ewm(span=26, adjust=False).mean()
        df['diff'] = df['ema12'] - df['ema26']
        df['dea'] = df['diff'].ewm(span=9, adjust=False).mean()
        df['macd'] = (df['diff'] - df['dea']) * 2
        return df

    @staticmethod
    def logic_macd_bottom(df):
        # 0轴下金叉
        return df['diff'].iloc[-1] < 0 and df['diff'].iloc[-2] < df['dea'].iloc[-2] and df['diff'].iloc[-1] > df['dea'].iloc[-1]

    @staticmethod
    def logic_duck_head(df):
        # MA5/10多头且回踩MA20（允许2%误差）
        ma20 = df['ma20'].iloc[-1]
        return df['ma5'].iloc[-1] > df['ma10'].iloc[-1] and ma20 < df['close'].iloc[-1] < ma20 * 1.03

    @staticmethod
    def logic_three_in_one(df):
        # 爆发：涨幅>4% + 倍量 + MACD 0轴上
        return df['pct_chg'].iloc[-1] > 4 and df['volume'].iloc[-1] > df['volume'].rolling(5).mean().iloc[-1] * 1.8 and df['diff'].iloc[-1] > 0

    @staticmethod
    def logic_pregnancy_line(df):
        # 底部孕线：今日高低点在昨日内
        return df['high'].iloc[-1] <= df['high'].iloc[-2] and df['low'].iloc[-1] >= df['low'].iloc[-2] and df['close'].iloc[-1] < df['ma60'].iloc[-1]

    @staticmethod
    def logic_single_yang(df):
        # 寻找最近10天内的大阳线且价格未跌破其低点
        recent = df.iloc[-10:]
        yang_mask = recent['pct_chg'] > 5
        if not yang_mask.any(): return False
        last_yang_low = recent[yang_mask].iloc[-1]['low']
        return df['close'].iloc[-1] >= last_yang_low

    @staticmethod
    def logic_limit_pullback(df):
        # 5天内有大涨且今日缩量回调
        recent_max_up = df['pct_chg'].iloc[-6:-1].max()
        return recent_max_up > 9.5 and df['volume'].iloc[-1] < df['volume'].iloc[-2] and abs(df['pct_chg'].iloc[-1]) < 3

    @staticmethod
    def logic_golden_pit(df):
        # 黄金坑：MA5从下穿MA34到站上MA5
        return df['close'].iloc[-5] < df['ma34'].iloc[-5] and df['close'].iloc[-1] > df['ma5'].iloc[-1]

    @staticmethod
    def logic_grass_fly(df):
        # 股价贴合MA60（3%误差）
        return abs(df['close'].iloc[-1] - df['ma60'].iloc[-1]) / df['ma60'].iloc[-1] < 0.03

    @staticmethod
    def logic_limit_break(df):
        # 跌破后3日内收回
        return df['close'].iloc[-1] > df['close'].iloc[-2] and df['pct_chg'].iloc[-3] > 9.5

    @staticmethod
    def logic_double_plate(df):
        # 阳-阴-阳组合
        return df['pct_chg'].iloc[-3] > 5 and df['pct_chg'].iloc[-2] < 0 and df['pct_chg'].iloc[-1] > 3

    @staticmethod
    def logic_horse_back(df):
        # 强势回踩：昨日大涨，今日踩5/10日线
        return df['pct_chg'].iloc[-2] > 7 and df['low'].iloc[-1] < df['ma10'].iloc[-1] * 1.02

    @staticmethod
    def logic_hot_money(df):
        # 倍量起航
        return df['volume'].iloc[-1] > df['volume'].iloc[-2] * 2

    @staticmethod
    def logic_wave_bottom(df):
        # 站上5日线且收盘价高于昨日
        return df['close'].iloc[-1] > df['ma5'].iloc[-1] and df['close'].iloc[-1] > df['close'].iloc[-2]

    @staticmethod
    def logic_no_loss(df):
        # 年线支撑（5%范围内）
        return abs(df['close'].iloc[-1] - df['ma250'].iloc[-1]) / df['ma250'].iloc[-1] < 0.05

    @staticmethod
    def logic_chase_rise(df):
        # 突破或接近20日高点
        return df['close'].iloc[-1] >= df['high'].iloc[-21:-1].max()

    @staticmethod
    def logic_inst_swing(df):
        # MACD红柱增长
        return df['macd'].iloc[-1] > df['macd'].iloc[-2] and df['macd'].iloc[-1] > 0

# --- 运行逻辑 ---
def run_all_strategies():
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
            if len(df) < 250: continue
            df = df.rename(columns={'日期':'date','股票代码':'code','开盘':'open','收盘':'close','成交量':'volume','涨跌幅':'pct_chg','换手率':'turnover'})
            code = os.path.basename(f).replace('.csv','')
            
            # 基础过滤：价格 5-45
            curr_close = df['close'].iloc[-1]
            if not (5.0 <= curr_close <= 45.0): continue
            
            df = AlphaLogics.get_indicators(df)
            
            for s_key in STRATEGY_MAP.keys():
                logic_func = getattr(AlphaLogics, f"logic_{s_key}")
                if logic_func(df):
                    all_results[s_key].append({
                        'date': date_str,
                        'code': code,
                        'name': name_map.get(code, '未知'),
                        'price': curr_close,
                        'pct_chg': df['pct_chg'].iloc[-1]
                    })
        except: continue

    for s_key, path in STRATEGY_MAP.items():
        if not os.path.exists(path): os.makedirs(path, exist_ok=True)
        res_df = pd.DataFrame(all_results[s_key])
        if not res_df.empty:
            res_df.to_csv(f"{path}/{s_key}_{date_str}.csv", index=False, encoding='utf-8-sig')
            print(f"战法 {s_key} 完成，发现 {len(res_df)} 个目标")
        else:
            print(f"战法 {s_key} 未发现目标")

if __name__ == "__main__":
    run_all_strategies()
