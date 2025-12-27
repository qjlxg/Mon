from DrissionPage import ChromiumPage, ChromiumOptions
import time
import os

def run_monitor():
    co = ChromiumOptions()
    co.set_argument('--headless')
    co.set_argument('--no-sandbox')
    co.set_user_agent('Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1') # 模拟手机UA，有时更易抓取

    page = ChromiumPage(co)
    keywords = ["ETF T+0", "ETF买卖", "ETF溢价"]
    targets = [
        {"platform": "微博", "url": "https://s.weibo.com/weibo?q="},
        {"platform": "雪球", "url": "https://xueqiu.com/k?q="}
    ]

    all_comments = []

    for target in targets:
        for kw in keywords:
            try:
                page.get(f"{target['url']}{kw}")
                page.wait.load_start()
                # 针对不同平台提取
                items = page.eles('.content') if target['platform'] == "微博" else page.eles('.status-item')
                
                for item in items[:5]:
                    text = item.text.replace('\n', ' ').strip()
                    if len(text) > 5:
                        all_comments.append({
                            "time": time.strftime('%m-%d %H:%M'),
                            "plat": target['platform'],
                            "kw": kw,
                            "cont": text
                        })
                time.sleep(2)
            except:
                continue

    # --- 生成适合手机观看的 README.md ---
    with open('README.md', 'w', encoding='utf-8') as f:
        f.write(f"# 📈 ETF 舆情实时监控\n\n")
        f.write(f"> 更新时间：{time.strftime('%Y-%m-%d %H:%M:%S')} (北京时间)\n\n")
        f.write(f"## 💬 最新评论 (TOP {len(all_comments)})\n\n")
        
        for c in all_comments:
            # 使用引用块排版，手机端阅读更清晰
            f.write(f"**[{c['plat']} - {c['kw']}]** *{c['time']}*\n")
            f.write(f"> {c['cont']}\n\n---\n")

    page.quit()

if __name__ == "__main__":
    run_monitor()
