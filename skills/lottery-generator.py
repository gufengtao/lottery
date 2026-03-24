#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双色球生成器 - 生成符合规则的双色球号码
自动避免与历史 300 期重复
"""

import json
import random
import sys
import argparse
from datetime import datetime
from pathlib import Path

# 设置标准输出为 UTF-8，避免 Windows 控制台编码问题
sys.stdout.reconfigure(encoding='utf-8')

# 获取脚本所在目录作为插件根目录
SCRIPT_DIR = Path(__file__).parent
HISTORY_PATH = SCRIPT_DIR.parent / 'data' / 'lottery-history.json'


def load_history(limit=300):
    """读取历史数据"""
    try:
        with open(HISTORY_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('history', [])[:limit]
    except Exception as e:
        print(f'❌ 无法读取历史数据：{e}')
        return []


def build_history_sets(history):
    """生成历史号码集合（用于去重）"""
    history_sets = set()
    for draw in history:
        red_tuple = tuple(sorted(draw['red_balls']))
        history_sets.add((red_tuple, draw['blue_ball']))
    return history_sets


def pad(n):
    """数字补零"""
    return f"{n:02d}"


def generate_number(last_red, last_blue, history_sets, options, recent_20=None, history=None):
    """
    生成一注符合规则的双色球号码

    Args:
        last_red: 上期红球列表
        last_blue: 上期蓝球
        history_sets: 历史号码集合
        options: 生成选项
        recent_20: 前 20 期红球集合（用于热度规则）
        history: 历史数据列表（用于蓝球遗漏和热度统计）
    """
    max_attempts = 10000
    repeat_count = options.get('repeat', random.randint(0, 2))
    # 连号：1-2 组随机（约 60-70% 概率开出连号）
    consecutive_groups = options.get('consecutive', random.choice([0, 1, 1, 2]))
    # 同尾号：约 50% 概率出现，非强制
    same_tail_groups = options.get('same_tail', random.choice([0, 0, 1, 1]))

    for _ in range(max_attempts):
        red_balls = set()

        # 1. 先从上期红球中选 repeat_count 个
        if repeat_count > 0 and last_red:
            selected_repeat = random.sample(list(last_red), min(repeat_count, len(last_red)))
            red_balls.update(selected_repeat)

        # 2. 生成剩余的红球
        remaining = 6 - len(red_balls)

        # 添加连续号码
        if consecutive_groups >= 1 and remaining >= 2:
            start = random.randint(1, 32)
            consecutive_pair = [pad(start), pad(start + 1)]
            if consecutive_pair[0] not in red_balls and consecutive_pair[1] not in red_balls:
                red_balls.update(consecutive_pair)
                remaining -= 2

        # 添加同尾号
        if same_tail_groups >= 1 and remaining >= 2:
            tail = random.randint(0, 9)
            same_tail = [pad(i) for i in range(1, 34)
                        if i % 10 == tail and pad(i) not in red_balls]
            if len(same_tail) >= 2:
                selected_tail = random.sample(same_tail, 2)
                red_balls.update(selected_tail)
                remaining -= 2

        # 补足剩余号码（优先选择前 20 期出现过的热号）
        while len(red_balls) < 6:
            available = [pad(i) for i in range(1, 34) if pad(i) not in red_balls]
            if not available:
                break
            # 如果有 recent_20 数据，优先选择热号
            if recent_20:
                hot_numbers = [n for n in available if n in recent_20]
                if hot_numbers and random.random() < 0.8:  # 80% 概率选热号
                    red_balls.add(random.choice(hot_numbers))
                else:
                    red_balls.add(random.choice(available))
            else:
                red_balls.add(random.choice(available))

        if len(red_balls) != 6:
            continue

        # 生成蓝球（考虑大小/奇偶交替 + 追热 + 遗漏回补）
        blue_available = [pad(i) for i in range(1, 17)]

        # 分析上期蓝球特征
        last_blue_num = int(last_blue)
        last_is_small = last_blue_num <= 8
        last_is_odd = last_blue_num % 2 == 1

        # 计算蓝球遗漏（多少期没开出）
        blue_omission = {}
        for b in range(1, 17):
            bb = pad(b)
            omission = 0
            for draw in history:
                if draw['blue_ball'] == bb:
                    break
                omission += 1
            blue_omission[bb] = omission

        # 统计前 30 期蓝球热度
        blue_heat = {}
        for b in range(1, 17):
            bb = pad(b)
            blue_heat[bb] = sum(1 for draw in history[:30] if draw['blue_ball'] == bb)

        # 蓝球选择策略（更均衡的概率分布）
        strategy = random.random()

        if strategy < 0.35:
            # 35% 概率：交替模式（大小/奇偶相反）
            if last_is_small:
                blue_available = [b for b in blue_available if int(b) > 8]
            else:
                blue_available = [b for b in blue_available if int(b) <= 8]
            if last_is_odd:
                blue_available = [b for b in blue_available if int(b) % 2 == 0]
            else:
                blue_available = [b for b in blue_available if int(b) % 2 == 1]
        elif strategy < 0.55:
            # 20% 概率：追热模式（选择近期热号）
            hot_blues = [b for b, heat in blue_heat.items() if heat >= 2]
            if hot_blues:
                blue_available = hot_blues
        elif strategy < 0.75:
            # 20% 概率：遗漏回补（选择遗漏 10 期以上的冷号）
            cold_blues = [b for b, omis in blue_omission.items() if omis >= 10]
            if cold_blues:
                blue_available = cold_blues
            else:
                blue_available = [b for b in blue_available if b != last_blue]
        else:
            # 25% 概率：追趋势（与上期同大小或同奇偶）
            if random.random() < 0.5:
                # 同大小
                if last_is_small:
                    blue_available = [b for b in blue_available if int(b) <= 8]
                else:
                    blue_available = [b for b in blue_available if int(b) > 8]
            else:
                # 同奇偶
                if last_is_odd:
                    blue_available = [b for b in blue_available if int(b) % 2 == 1]
                else:
                    blue_available = [b for b in blue_available if int(b) % 2 == 0]

        blue_ball = random.choice(blue_available) if blue_available else pad(random.randint(1, 16))

        # 检查是否与历史 300 期重复
        red_tuple = tuple(sorted(red_balls))
        if (red_tuple, blue_ball) in history_sets:
            continue

        # 验证规则
        red_list = sorted(red_balls, key=int)
        repeat_reds = [r for r in red_list if r in last_red]

        # 计算连续号码组数
        consecutive_count = 0
        for i in range(len(red_list) - 1):
            if int(red_list[i + 1]) - int(red_list[i]) == 1:
                consecutive_count += 1

        # 计算同尾号
        tail_dict = {}
        for r in red_list:
            tail = int(r) % 10
            if tail not in tail_dict:
                tail_dict[tail] = []
            tail_dict[tail].append(r)
        same_tail_pairs = [(tail, nums) for tail, nums in tail_dict.items()
                          if len(nums) >= 2]

        return {
            'red_balls': red_list,
            'blue_ball': blue_ball,
            'repeat_reds': repeat_reds,
            'consecutive_count': consecutive_count,
            'same_tail_pairs': same_tail_pairs
        }

    return None


def format_output(result, issue_num, index=None):
    """格式化输出结果"""
    output = []

    if index is not None:
        output.append(f"\n【第 {index} 注】")

    output.append(f"红球：{'  '.join(result['red_balls'])}")
    output.append(f"蓝球：{result['blue_ball']}")
    output.append("规则验证:")

    repeat_str = ', '.join(result['repeat_reds']) if result['repeat_reds'] else '无'
    output.append(f"  ✅ 重复上期：{repeat_str}")

    output.append(f"  ✅ 连续号码：{result['consecutive_count']} 组")

    if result['same_tail_pairs']:
        for tail, nums in result['same_tail_pairs']:
            output.append(f"  ✅ 同尾号：{', '.join(nums)} (尾数 {tail})")
    else:
        output.append("  ✅ 同尾号：无")

    return '\n'.join(output)


def main():
    parser = argparse.ArgumentParser(description='双色球生成器')
    parser.add_argument('--last-red', type=str, help='上期红球号码（逗号分隔）')
    parser.add_argument('--last-blue', type=str, help='上期蓝球号码')
    parser.add_argument('--repeat', type=int, help='重复上期红球数量')
    parser.add_argument('--consecutive', type=int, default=1, help='连续号码组数')
    parser.add_argument('--same-tail', type=int, default=1, help='同尾号组数')
    parser.add_argument('--count', type=int, default=1, help='生成注数')

    args = parser.parse_args()

    # 读取历史数据
    history = load_history(300)
    if not history:
        print('❌ 没有历史数据，请先运行 /lottery-update 更新数据')
        sys.exit(1)

    # 获取上期号码
    latest = history[0]
    last_red = set(latest['red_balls'])
    last_blue = latest['blue_ball']

    # 提取前 20 期红球（用于热度规则）
    recent_20_reds = set()
    for draw in history[1:21]:  # 排除最新一期，取后面 20 期
        recent_20_reds.update(draw['red_balls'])

    # 如果用户指定了上期号码，使用用户的
    if args.last_red:
        last_red = set(args.last_red.split(','))
    if args.last_blue:
        last_blue = args.last_blue

    print(f"参考上期（{latest['issue']}期 {latest['date']}）: "
          f"红球 {' '.join(latest['red_balls'])} 蓝球 {last_blue}")
    print()

    # 构建历史号码集合
    history_sets = build_history_sets(history)

    # 生成选项
    options = {
        'repeat': args.repeat if args.repeat is not None else random.randint(0, 2),
        'consecutive': args.consecutive,
        'same_tail': args.same_tail
    }

    next_issue = int(latest['issue']) + 1

    # 生成单注还是多注
    if args.count == 1:
        result = generate_number(last_red, last_blue, history_sets, options, recent_20_reds, history)
        if result:
            print(format_output(result, next_issue))
        else:
            print('❌ 无法生成符合条件的号码，请调整规则参数')
            sys.exit(1)
    else:
        # 生成多注
        print("=" * 50)
        print(f"双色球推荐号码（第 {next_issue} 期）")
        print("=" * 50)

        for i in range(args.count):
            result = generate_number(last_red, last_blue, history_sets, options, recent_20_reds, history)
            if result:
                print(format_output(result, next_issue, i + 1))

        print("\n" + "=" * 50)
        print(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)


if __name__ == '__main__':
    main()
