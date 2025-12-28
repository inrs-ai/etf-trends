# main.py
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.font_manager as fm
from datetime import datetime
import time

# ==================== 1. 环境与字体配置 ====================
# GitHub Actions Linux环境需要加载本地字体文件
font_path = 'SimHei.ttf'
if os.path.exists(font_path):
    my_font = fm.FontProperties(fname=font_path)
    plt.rcParams['font.sans-serif'] = [my_font.get_name()]
else:
    # 如果本地没有字体文件（回退方案），使用默认
    plt.rcParams['font.sans-serif'] = ['sans-serif']
    print("警告：未找到 SimHei.ttf，中文可能乱码")

plt.rcParams['axes.unicode_minus'] = False

# ==================== 2. ETF 列表 ====================
etf_info = {
    "516970": "基建50ETF", "159745": "建材ETF", "515210": "钢铁ETF",
    "515220": "煤炭ETF", "516150": "稀土ETF", "159870": "化工ETF",
    "560280": "工程机械ETF", "512880": "证券ETF", "512800": "银行ETF",
    "159611": "电力ETF", "159755": "电池ETF", "159992": "创新药ETF",
    "159996": "家电ETF", "515170": "食品饮料ETF", "516110": "汽车ETF",
    "159995": "芯片ETF", "515880": "通信ETF", "159819": "人工智能ETF",
    "562500": "机器人ETF", "515230": "软件ETF", "516010": "游戏ETF",
    "510300": "沪深300ETF", "159949": "创业板50ETF", "588000": "科创50ETF"
}
urls = [f"https://www.jisilu.cn/data/etf/detail/{code}" for code in etf_info]

# ==================== 3. 驱动配置 (适配 GitHub Actions) ====================
options = Options()
options.add_argument('--headless')
options.add_argument('--disable-gpu')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage') # 解决资源限制问题
options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')

driver = webdriver.Chrome(options=options)
driver.implicitly_wait(10)

# ==================== 4. 数据采集 ====================
all_data = {}
print("开始抓取数据...")

for url in urls:
    code = url.split('/')[-1]
    name = etf_info[code]
    print(f"正在处理: {name} ({code})")
    
    try:
        driver.get(url)
        # 适当减少等待时间，提高效率
        time.sleep(2) 
        
        # 尝试点击“历史规模”
        try:
            tab = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(),'历史规模')]"))
            )
            tab.click()
            time.sleep(2)
        except:
            pass 

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        table = None
        for t in soup.find_all('table'):
            if '场内份额' in t.text:
                table = t
                break
        
        if not table:
            continue
            
        rows = table.find_all('tr')[1:181] # 最近180天
        dates, shares = [], []
        for row in rows:
            cols = [c.text.strip().replace(',', '').replace(' ', '') for c in row.find_all('td')]
            if len(cols) >= 6:
                try:
                    date_str = cols[0].split()[0].replace('/', '-')
                    date = datetime.strptime(date_str, '%Y-%m-%d')
                    share = float(cols[5].replace('万', ''))
                    dates.append(date)
                    shares.append(share)
                except:
                    continue
        
        if len(dates) > 5:
            df = pd.DataFrame({'Date': dates, 'Share': shares}).drop_duplicates().sort_values('Date').tail(180)
            all_data[code] = {'name': name, 'df': df}

    except Exception as e:
        print(f"Error grabbing {code}: {e}")

driver.quit()

if not all_data:
    print("无数据，退出")
    exit(1)

# ==================== 5. 生成图片 ====================
print("正在绘图...")
# 设置画布大小 (3列8行)
fig = plt.figure(figsize=(20, 40)) # 增加高度以容纳清晰的图表
gs = fig.add_gridspec(8, 3, hspace=0.4, wspace=0.2)

for idx, (code, info) in enumerate(all_data.items()):
    row, col = divmod(idx, 3)
    if row >= 8: break
    
    ax = fig.add_subplot(gs[row, col])
    df = info['df']
    
    # 绘图
    ax.plot(df['Date'], df['Share'], 'o-', linewidth=2, markersize=4, color='#0066CC')
    
    # 标注最新值
    latest = df.iloc[-1]
    ax.annotate(f'{latest["Share"]:.0f}', 
                (latest['Date'], latest['Share']),
                xytext=(5, 5), textcoords='offset points',
                fontsize=10, color='red', fontweight='bold',
                fontproperties=my_font if os.path.exists(font_path) else None,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#FFFFDD", alpha=0.9))
    
    # 标题和标签
    title_str = f"{code} {info['name']}"
    ax.set_title(title_str, fontsize=14, fontweight='bold', fontproperties=my_font if os.path.exists(font_path) else None)
    ax.grid(True, alpha=0.3)
    
    # 日期格式化
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=30)

# 顶部大标题
fig.suptitle(f'ETF场内份额趋势追踪 (更新时间: {datetime.now().strftime("%Y-%m-%d %H:%M")})', 
             fontsize=24, fontweight='bold', y=0.90, fontproperties=my_font if os.path.exists(font_path) else None)

# 保存图片
img_filename = 'etf_trends.png'
plt.savefig(img_filename, bbox_inches='tight', dpi=100)
plt.close()

# ==================== 6. 生成 HTML 网页 ====================
print("正在生成 HTML...")

# 计算排名
ranked = sorted(all_data.items(), key=lambda x: x[1]['df']['Share'].iloc[-1], reverse=True)
top_list_html = ""
for idx, (code, info) in enumerate(ranked):
    share = info['df']['Share'].iloc[-1]
    # 前3名红色高亮
    color = "red" if idx < 3 else "black"
    weight = "bold" if idx < 3 else "normal"
    top_list_html += f"<li style='color:{color}; font-weight:{weight};'>{idx+1}. {info['name']} ({code}): {share:,.0f} 万份</li>\n"

html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ETF 份额日报</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background-color: #f4f4f4; }}
        h1 {{ text-align: center; color: #333; }}
        .update-time {{ text-align: center; color: #666; margin-bottom: 20px; }}
        .container {{ display: flex; flex-wrap: wrap; justify-content: center; }}
        .chart-box {{ width: 100%; text-align: center; background: white; padding: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); margin-bottom: 20px; }}
        .rank-box {{ width: 100%; background: white; padding: 20px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
        .rank-list {{ column-count: 3; column-gap: 40px; list-style-type: none; padding: 0; }}
        .rank-list li {{ padding: 5px 0; border-bottom: 1px solid #eee; }}
        img {{ max-width: 100%; height: auto; }}
        
        @media (max-width: 768px) {{
            .rank-list {{ column-count: 1; }}
        }}
    </style>
</head>
<body>
    <h1>ETF 场内份额每日追踪</h1>
    <div class="update-time">更新时间 (北京时间): {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
    
    <div class="rank-box">
        <h3>📊 最新份额排名</h3>
        <ul class="rank-list">
            {top_list_html}
        </ul>
    </div>

    <div class="chart-box">
        <img src="{img_filename}" alt="ETF Trends Chart">
    </div>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("完成！")
