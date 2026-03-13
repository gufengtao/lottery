import requests
from bs4 import BeautifulSoup
import json
import os
import sys
from datetime import datetime

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8')

print("正在从中国福彩网同步双色球历史数据...")

base_url = "https://kaijiang.zhcw.com/zhcw/html/ssq/list_{}.html"
all_draws = []

for page in range(1, 20):
    url = base_url.format(page)
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://kaijiang.zhcw.com/'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'

        soup = BeautifulSoup(response.text, 'html.parser')
        rows = soup.select('table.wqhgt tr')

        count = 0
        for row in rows[2:]:
            try:
                cols = row.select('td')
                if len(cols) >= 7:
                    date = cols[0].text.strip()
                    issue = cols[1].text.strip()
                    red_balls = [em.text for em in row.select('em.rr')]
                    blue_ball_elem = row.select('em:not(.rr)')
                    blue_ball = blue_ball_elem[0].text.strip() if blue_ball_elem else ''

                    if issue and len(red_balls) == 6 and blue_ball:
                        all_draws.append({
                            'date': date,
                            'issue': issue,
                            'red_balls': red_balls,
                            'blue_ball': blue_ball
                        })
                        count += 1
            except:
                continue

        print(f'页{page}: {count}期')
        if count == 0:
            break
    except Exception as e:
        print(f'页{page}: 错误 {e}')
        continue

print(f'\n总计：{len(all_draws)}期')

# 获取插件目录的 data 路径
script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(script_dir, 'data')
os.makedirs(data_dir, exist_ok=True)

new_draws = [{
    'date': draw['date'],
    'issue': draw['issue'],
    'red_balls': draw['red_balls'],
    'blue_ball': draw['blue_ball']
} for draw in all_draws]

# 加载现有历史数据（如果有）
output_file = os.path.join(data_dir, 'lottery-history.json')
existing_history = []
if os.path.exists(output_file):
    try:
        with open(output_file, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
            existing_history = existing_data.get('history', [])
        print(f'[OK] 已加载 {len(existing_history)} 期历史数据')
    except:
        print('[WARN] 无法加载现有数据，将创建新文件')

# 合并数据：新数据 + 现有数据（去重）
existing_issues = {draw['issue'] for draw in existing_history}
merged_history = []

# 添加新数据（不重复）
for draw in new_draws:
    if draw['issue'] not in existing_issues:
        merged_history.append(draw)
        existing_issues.add(draw['issue'])

# 追加现有数据
merged_history.extend(existing_history)

# 按期号降序排序（最新的在前）
merged_history.sort(key=lambda x: int(x['issue']), reverse=True)

# 保存合并后的数据
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump({
        'history': merged_history,
        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'source': '中国福彩网官方 (kaijiang.zhcw.com)'
    }, f, ensure_ascii=False, indent=2)

print(f'\n[OK] 已保存到：{output_file}')
new_count = len(merged_history) - len(existing_history)
print(f'[INFO] 本期新增 {new_count} 期')
print(f'[INFO] 总计 {len(merged_history)} 期历史数据（追加模式，不删除旧数据）')

if merged_history:
    latest = merged_history[0]
    print(f'\n[LATEST] 期号：{latest["issue"]} ({latest["date"]})')
    print(f'   红球：{" ".join(latest["red_balls"])}')
    print(f'   蓝球：{latest["blue_ball"]}')

    if len(merged_history) > 1:
        earliest = merged_history[-1]
        print(f'\n[FIRST] 期号：{earliest["issue"]} ({earliest["date"]})')
