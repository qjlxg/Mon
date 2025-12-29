import pandas as pd
import os
from datetime import datetime
import glob

# 配置文件夹路径 - 保持不变
STRATEGIES = {
    'one_sun': 'results/one_sun',
    'macd_water': 'results/macd_water',
    'golden_pit': 'results/golden_pit',
    'duck_hunter': 'results/duck_hunter'
}

OUTPUT_FILE = 'results/confluence_report.csv'

# 各战法的实战操作手册 - 保持不变
OPERATIONS = {
    'one_sun': "【爆发位】一阳穿三线。次日看高开(1%-3%)，放量突破昨日最高价即是买点。止损设在阳线一半位置。",
    'macd_water': "【强势位】水上金叉/红柱放大。代表多头趋势延续。若股价贴近20日线可回吸，跌破20日线或MACD死叉离场。",
    'golden_pit': "【底部位】黄金坑企稳。属于左侧交易，适合潜伏。今日放量阳线确认坑底，跌破坑底最低价止损。",
    'duck_hunter': "【波段位】老鸭头形态。极品形态，鸭嘴张开是主升浪起点。止损设在鸭嘴下沿（MA10或MA20）。"
}

def get_latest_file(folder):
    """获取文件夹内最新的CSV文件"""
    files = glob.glob(f"{folder}/*.csv")
    if not files: return None
    return max(files)

def main():
    confluence_data = []
    
    # 1. 汇总所有战法的最新结果 - 保持不变
    for name, path in STRATEGIES.items():
        latest_file = get_latest_file(path)
        if latest_file:
            try:
                df = pd.read_csv(latest_file)
                if not df.empty:
                    df['code'] = df['code'].astype(str).str.zfill(6)
                    for _, row in df.iterrows():
                        confluence_data.append({
                            'code': row['code'],
                            'name': row.get('name', '未知'),
                            'strategy': name
                        })
            except Exception as e:
                print(f"解析 {latest_file} 出错: {e}")

    if not confluence_data:
        print("今日无任何战法选出股票。")
        return

    # 2. 统计共振频率 - 保持不变
    all_df = pd.DataFrame(confluence_data)
    report = all_df.groupby(['code', 'name'])['strategy'].apply(list).reset_index()
    report['resonance_count'] = report['strategy'].apply(len)
    
    # 3. 关联操作方法 - 保持不变
    def attach_op(strategies):
        ops = []
        for s in strategies:
            ops.append(f"[{s}]: {OPERATIONS[s]}")
        return " | ".join(ops)

    report['action_guide'] = report['strategy'].apply(attach_op)
    report['strategy_list'] = report['strategy'].apply(lambda x: ",".join(x))

    # 4. 排序：共振次数越多越靠前
    report = report.sort_values(by=['resonance_count', 'code'], ascending=[False, True])

    # 5. 保存完整结果到CSV (utf-8-sig 确保不乱码) - 保持不变
    os.makedirs('results', exist_ok=True)
    report.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
    
    # 6. 控制台强化版分级汇报 - 针对55只以上的情况进行视觉优化
    print("\n" + "="*50)
    print(f"  大海捞鱼 - 共振精选报告 ({datetime.now().strftime('%Y-%m-%d')})")
    print("="*50)

    # 分级筛选展示
    lv3 = report[report['resonance_count'] >= 3]
    lv2 = report[report['resonance_count'] == 2]

    if not lv3.empty:
        print(f"💎 【核心标的 (3重共振及以上)】 数量: {len(lv3)}")
        for _, r in lv3.iterrows():
            print(f" >> 代码: {r['code']} | 名称: {r['name']} | 战法: {r['strategy_list']}")
        print("-" * 30)
    
    if not lv2.empty:
        print(f"🔥 【重点关注 (2重共振)】 数量: {len(lv2)}")
        # 如果2重共振票太多（超过15只），只打印前15只，防止刷屏
        display_lv2 = lv2.head(15)
        for _, r in display_lv2.iterrows():
            print(f" -> 代码: {r['code']} | 名称: {r['name']}")
        if len(lv2) > 15:
            print(f" ...等共 {len(lv2)} 只，完整列表请查看 results/confluence_report.csv")
    
    print("="*50)
    print(f"报告已更新至: {OUTPUT_FILE}\n")

if __name__ == "__main__":
    main()
