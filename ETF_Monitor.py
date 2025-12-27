from DrissionPage import ChromiumPage, ChromiumOptions
import time
import os

def run_monitor():
    # 配置浏览器：模拟手机端，增加成功率
    co = ChromiumOptions()
    co.set_argument('--headless')
    co.set_argument('--no-sandbox')
    co.set_user_agent('Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1')

    page = ChromiumPage(co)
    keywords = ["ETF T+0", "ETF买卖", "ETF溢价"]
    targets = [
        {"platform": "微博", "icon": "📱", "url": "https://s.weibo.com/weibo?q="},
        {"platform": "雪球", "icon": "❄️", "url": "https://xueqiu.com/k?q="}
    ]

    all_comments = []

    for target in targets:
        for kw in keywords:
            try:
                page.get(f"{target['url']}{kw}")
                page.wait.load_start()
                
                # 微博和雪球的选择器适配
                items = page.eles('.content') if target['platform'] == "微博" else page.eles('.status-item')
                
                for item in items[:6]:  # 每个关键词取前6条最新评论
                    text = item.text.replace('\n', ' ').strip()
                    if len(text) > 10:  # 过滤太短的无意义内容
                        all_comments.append({
                            "time": time.strftime('%H:%M'),
                            "plat": target['platform'],
                            "icon": target['icon'],
                            "kw": kw,
                            "cont": text
                        })
                time.sleep(1)
            except Exception as e:
                print(f"抓取 {target['platform']} - {kw} 出错: {e}")
                continue

    # --- 写入 README.md (适配手机观看) ---
    with open('README.md', 'w', encoding='utf-8') as f:
        f.write(f"# 📊 ETF 实时舆情监控\n\n")
        f.write(f"> 🕒 **最后更新时间**：{time.strftime('%Y-%m-%d %H:%M:%S')} (北京时间)\n\n")
        f.write(f"---\n\n")
        
        if not all_comments:
            f.write("⚠️ 暂时没有抓取到新数据，可能是由于 IP 限制。")
        else:
            for c in all_comments:
                # 使用标题和引用块，手机端会有明显的层次感
                f.write(f"### {c['icon']} {c['plat']} | 📌 #{c['kw']}#\n")
                f.write(f"**发布时间**：`今日 {c['time']}`\n\n")
                f.write(f"> {c['cont']}\n\n")
                f.write(f"---\n") # 分割线

    page.quit()

if __name__ == "__main__":
    run_monitor()
