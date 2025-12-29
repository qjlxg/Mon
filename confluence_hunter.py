import pandas as pd
import os
import glob
from datetime import datetime

# 策略路径配置
STRATEGIES = {
    'one_sun': 'results/one_sun',
    'macd_water': 'results/macd_water',
    'golden_pit': 'results/golden_pit',
    'duck_hunter': 'results/duck_hunter'
}

REPORT_PATH = 'results/confluence_report.csv'
HISTORY_DIR = 'history'
HISTORY_FILE = os.path.join(HISTORY_DIR, 'resonance_history.csv')
STATS_FILE = os.path.join(HISTORY_DIR, 'overall_stats.txt') # 用于保存累计收益

# 操作指南
OPERATIONS = {
    'one_sun': "【爆发位】一阳穿三线。次日看高开(1%-3%)，放量突破昨日最高价即是买点。",
    'macd_water': "【强势位】水上金叉。代表多头趋势延续。若股价贴近20日线可回吸。",
    'golden_pit': "【底部位】黄金坑企稳。适合底部轻仓潜伏，跌破坑底最低价止损。",
    'duck_hunter': "【波段位】老鸭头形态。鸭嘴张开是主升浪起点。止损设在鸭嘴下沿。"
}

def get_latest_file(folder):
    files = glob.glob(f"{folder}/*.csv")
    return max(files) if files else None

def get_total_gain():
    """从本地读取累计收益率"""
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, 'r') as f:
            try:
                return float(f.read().strip())
            except:
                return 0.0
    return 0.0

def save_total_gain(gain):
    """保存更新后的累计收益率"""
    with open(STATS_FILE, 'w') as f:
        f.write(f"{gain:.2f}")

def main():
    all_picks = []
    
    # 1. 汇总今日各战法结果
    for name, path in STRATEGIES.items():
        latest = get_latest_file(path)
        if latest:
            try:
                df = pd.read_csv(latest)
                df['code'] = df['code'].astype(str).str.zfill(6)
                for _, row in df.iterrows():
                    all_picks.append({
                        'date': row.get('filter_date', datetime.now().strftime('%Y-%m-%d')),
                        'code': row['code'],
                        'name': row.get('name', '未知'),
                        'strategy': name,
                        'price': row.get('price', 0)
                    })
            except: continue

    if not all_picks:
        print("今日无选股结果，跳过分析。")
        return

    # 2. 生成今日共振报告
    df_all = pd.DataFrame(all_picks)
    today_report = df_all.groupby(['date', 'code', 'name']).agg({
        'strategy': lambda x: ','.join(x),
        'price': 'first'
    }).reset_index()
    
    today_report['resonance_count'] = today_report['strategy'].apply(lambda x: len(x.split(',')))
    
    def get_guide(strategies):
        guides = [f"[{s}]: {OPERATIONS.get(s, '')}" for s in strategies.split(',')]
        return " | ".join(guides)
    
    today_report['action_guide'] = today_report['strategy'].apply(get_guide)
    today_report = today_report.sort_values(by=['resonance_count', 'code'], ascending=[False, True])

    # 3. 战果统计 (复盘昨日) & 累计收益计算
    os.makedirs(HISTORY_DIR, exist_ok=True)
    performance_msg = "首次运行或今日无新对账数据。"
    total_gain = get_latest_total = get_total_gain()
    
    if os.path.exists(HISTORY_FILE):
        hist_df = pd.read_csv(HISTORY_FILE, dtype={'code': str})
        last_date = hist_df['date'].max()
        if last_date != today_report['date'].iloc[0]:
            last_picks = hist_df[hist_df['date'] == last_date].copy()
            merged = pd.merge(last_picks, today_report[['code', 'price']], on='code', suffixes=('_old', '_now'))
            if not merged.empty:
                merged['gain'] = ((merged['price_now'] - merged['price_old']) / merged['price_old'] * 100).round(2)
                avg_gain = merged['gain'].mean()
                win_rate = (len(merged[merged['gain'] > 0]) / len(merged)) * 100
                # 更新累计总收益 (简单累加)
                total_gain += avg_gain
                save_total_gain(total_gain)
                performance_msg = f"昨日精选今日平均涨幅: {avg_gain:.2f}% | 胜率: {win_rate:.1f}%"

    # 4. 更新历史总账 (建立错题集)
    if os.path.exists(HISTORY_FILE):
        full_history = pd.read_csv(HISTORY_FILE, dtype={'code': str})
        full_history = full_history[full_history['date'] != today_report['date'].iloc[0]]
        full_history = pd.concat([full_history, today_report], ignore_index=True)
    else:
        full_history = today_report
    full_history.to_csv(HISTORY_FILE, index=False, encoding='utf-8-sig')

    # 5. 保存今日精选到 results/
    today_report.to_csv(REPORT_PATH, index=False, encoding='utf-8-sig')

    # 6. 控制台汇报
    print("\n" + "="*50)
    print(f"  📊 大海捞鱼 - 自动化复盘报告 ({today_report['date'].iloc[0]})")
    print(f"  📈 {performance_msg}")
    print(f"  🏆 系统上线以来累计总收益率: {total_gain:.2f}%")
    print("="*50)
    
    top_v = today_report[today_report['resonance_count'] >= 3]
    if not top_v.empty:
        print(f"💎 今日【核心共振】(3重以上):")
        for _, r in top_v.iterrows():
            print(f" >> {r['code']} | {r['name']} | 现价: {r['price']} | 战法: {r['strategy']}")
    
    print(f"🔥 今日 2 重共振标的: {len(today_report[today_report['resonance_count'] == 2])} 只")
    print(f"📂 历史错题集(对账单): {HISTORY_FILE}")
    print("="*50 + "\n")

if __name__ == "__main__":
    main()
