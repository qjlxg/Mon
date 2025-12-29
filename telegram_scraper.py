import os
import requests
from bs4 import BeautifulSoup
import easyocr
import datetime
import time

# 初始化 OCR (仅使用 CPU)
try:
    # 第一次运行会自动下载模型，yml 中已配置缓存
    reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)
except Exception as e:
    print(f"OCR 初始化失败: {e}")
    reader = None

channels = ['ChinaStock3000', 'Guanshuitan', 'gainiantuhua', 'hgclhyyb']

def get_channel_content(channel_name):
    print(f"--- 正在抓取频道: {channel_name} ---")
    url = f"https://t.me/s/{channel_name}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=30)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        # 兼容多种消息容器类名
        messages = soup.select('.tgme_widget_message_wrap, .tgme_widget_message')
        
        if not messages:
            return f"## 来源: {channel_name}\n> 未抓取到内容，可能存在访问限制。\n\n---\n\n"
    except Exception as e:
        return f"## 来源: {channel_name}\n> 访问异常: {e}\n\n---\n\n"
    
    output = f"## 来源: {channel_name}\n\n"
    # 获取最后 10 条消息
    for msg in messages[-10:]:
        # 1. 提取文字（包含普通消息和带格式的消息）
        text_div = msg.find('div', class_=['tgme_widget_message_text', 'tgme_widget_message_bubble'])
        text = text_div.get_text(separator="\n").strip() if text_div else ""
        
        # 2. 提取图片并进行 OCR
        ocr_result = ""
        # 针对图片链接的多种可能类名
        img_tag = msg.find('a', class_=['tgme_widget_message_photo_step', 'tgme_widget_message_photo'])
        if img_tag and reader:
            style = img_tag.get('style', '')
            if "url('" in style:
                img_url = style.split("url('")[1].split("')")[0]
                try:
                    # 避免请求过快
                    img_res = requests.get(img_url, timeout=15)
                    img_path = "temp_img.jpg"
                    with open(img_path, "wb") as f:
                        f.write(img_res.content)
                    
                    # 识别文字，detail=0 只返回文本列表
                    lines = reader.readtext(img_path, detail=0)
                    if lines:
                        ocr_result = "\n\n> **[图片识别文字]**：\n> " + "\n> ".join(lines)
                    os.remove(img_path)
                except Exception as e:
                    print(f"图片 OCR 失败: {e}")

        if text or ocr_result:
            output += f"{text}{ocr_result}\n\n---\n\n"
            
    return output

def main():
    # 上海时区处理
    sh_tz = datetime.timezone(datetime.timedelta(hours=8))
    now = datetime.datetime.now(sh_tz)
    sh_time_str = now.strftime('%Y-%m-%d %H:%M:%S')
    
    header = f"# Telegram 内容自动汇总\n\n**更新时间 (北京时间): {sh_time_str}**\n\n"
    full_body = ""
    
    for channel in channels:
        full_body += get_channel_content(channel)
        time.sleep(2) # 频道间微量延迟，防屏蔽
        
    # 写入 README.md
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(header + full_body)
    
    # 写入历史目录
    history_dir = "history"
    if not os.path.exists(history_dir):
        os.makedirs(history_dir)
    
    history_file = f"{history_dir}/{now.strftime('%Y-%m-%d')}.md"
    with open(history_file, "a", encoding="utf-8") as f:
        f.write(f"\n\n### 抓取时点: {sh_time_str}\n\n" + full_body)

if __name__ == "__main__":
    main()
