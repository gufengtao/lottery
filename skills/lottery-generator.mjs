import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// ============== 配置 ==============
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const HISTORY_PATH = path.join(__dirname, '..', 'data', 'lottery-history.json');

// ============== 工具函数 ==============

/**
 * 生成范围内的随机整数
 */
function rand(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

/**
 * 数字补零格式化
 */
function pad(n) {
  return n.toString().padStart(2, '0');
}

/**
 * 获取号码尾数
 */
function getTail(n) {
  return parseInt(n) % 10;
}

/**
 * 检查是否有指定长度的连续号码
 */
function hasConsecutive(balls, count) {
  let consecutive = 0;
  let maxConsecutive = 0;
  for (let i = 1; i < balls.length; i++) {
    if (parseInt(balls[i]) - parseInt(balls[i - 1]) === 1) {
      consecutive++;
      maxConsecutive = Math.max(maxConsecutive, consecutive);
    } else {
      consecutive = 0;
    }
  }
  return maxConsecutive >= count - 1;
}

/**
 * 获取同尾号组数
 */
function getSameTailGroups(balls, minGroupSize = 2) {
  const tails = {};
  balls.forEach((b) => {
    const t = getTail(b);
    if (!tails[t]) tails[t] = [];
    tails[t].push(b);
  });
  let groups = 0;
  for (const t in tails) {
    if (tails[t].length >= minGroupSize) groups++;
  }
  return groups;
}

/**
 * 计算两组号码的重复数量
 */
function countRepeat(balls1, balls2) {
  return balls1.filter((b) => balls2.includes(b)).length;
}

/**
 * 查找所有连续号码对
 */
function findConsecutivePairs(balls) {
  const pairs = [];
  for (let i = 1; i < balls.length; i++) {
    if (parseInt(balls[i]) - parseInt(balls[i - 1]) === 1) {
      pairs.push([balls[i - 1], balls[i]]);
    }
  }
  return pairs;
}

/**
 * 查找所有同尾号组合
 */
function findSameTailGroups(balls) {
  const tails = {};
  balls.forEach((b) => {
    const t = getTail(b);
    if (!tails[t]) tails[t] = [];
    tails[t].push(b);
  });
  const groups = [];
  for (const t in tails) {
    if (tails[t].length >= 2) {
      groups.push({ tail: t, balls: tails[t] });
    }
  }
  return groups;
}

// ============== 核心生成逻辑 ==============

/**
 * 读取历史数据
 */
function loadHistory() {
  try {
    const data = JSON.parse(fs.readFileSync(HISTORY_PATH, 'utf-8'));
    return data.history || [];
  } catch (e) {
    console.error('❌ 无法读取历史数据:', e.message);
    return [];
  }
}

/**
 * 生成历史红球组合的 Set（用于快速查重）
 */
function buildHistoryCombos(history) {
  return new Set(history.map((h) => h.red_balls.slice().sort().join(',')));
}

/**
 * 生成红球号码
 */
function generateRedBalls(historyCombos, options) {
  const { lastRed = [], repeat = 2, consecutive = 1, sameTail = 1 } = options;
  const maxAttempts = 10000;
  let attempts = 0;

  while (attempts < maxAttempts) {
    attempts++;

    // 策略性选择：确保有指定的重复号码数
    const lastRedNums = lastRed.map((r) => parseInt(r));

    // 先从上期号码中选择指定数量的重复球
    const repeatedCount = Math.min(repeat, lastRed.length, 6);
    const shuffledLast = lastRedNums.sort(() => Math.random() - 0.5);
    const selectedNums = new Set();

    for (let i = 0; i < repeatedCount; i++) {
      selectedNums.add(shuffledLast[i]);
    }

    // 补充剩余号码
    while (selectedNums.size < 6) {
      const num = rand(1, 33);
      selectedNums.add(num);
    }

    const selected = Array.from(selectedNums)
      .sort((a, b) => a - b)
      .map((n) => pad(n));

    // 检查是否与历史重复
    const combo = selected.join(',');
    if (historyCombos.has(combo)) continue;

    // 检查连续号码
    if (!hasConsecutive(selected, consecutive + 1)) continue;

    // 检查同尾号
    if (getSameTailGroups(selected, 2) < sameTail) continue;

    return selected;
  }

  return null;
}

/**
 * 生成蓝球号码
 */
function generateBlueBall(exclude, lastBlue) {
  const excludeNum = exclude ? parseInt(exclude) : lastBlue ? parseInt(lastBlue) : -1;
  const pool = Array.from({ length: 16 }, (_, i) => i + 1).filter((n) => n !== excludeNum);
  return pad(pool[rand(0, pool.length - 1)]);
}

/**
 * 验证生成结果
 */
function validate(generated, lastRed, lastBlue) {
  const { redBalls, blueBall } = generated;

  const repeatCount = countRepeat(redBalls, lastRed);
  const consecPairs = findConsecutivePairs(redBalls);
  const sameTailGroups = findSameTailGroups(redBalls);

  return {
    repeat: repeatCount,
    hasConsec: consecPairs.length > 0,
    consecPairs,
    hasSameTail: sameTailGroups.length > 0,
    sameTailGroups,
    blueNotRepeat: blueBall !== lastBlue,
  };
}

/**
 * 格式化输出
 */
function formatOutput(generated, validation, lastRed) {
  const { redBalls, blueBall } = generated;

  const repeatBalls = redBalls.filter((b) => lastRed.includes(b));
  const consecStr = validation.consecPairs.map((p) => p.join(', ')).join('; ') || '无';
  const sameTailStr = validation.sameTailGroups
    .map((g) => `${g.balls.join(', ')} (尾数${g.tail})`)
    .join('; ') || '无';

  let output = '\n';
  output += '双色球号码\n';
  output += '═══════════════════\n';
  output += `红球：${redBalls.join('  ')}\n`;
  output += `蓝球：${blueBall}\n`;
  output += '═══════════════════\n';
  output += '规则验证:\n';
  output += `  ✅ 重复上期：${validation.repeat} 个 (${repeatBalls.join(', ') || '无'})\n`;
  output += `  ✅ 连续号码：${consecStr}\n`;
  output += `  ✅ 同尾号：${sameTailStr}\n`;
  output += `  ${validation.blueNotRepeat ? '✅' : '⚠️'} 蓝球${validation.blueNotRepeat ? '不' : ''}跟上期重复\n`;
  output += '\n';

  return output;
}

// ============== 主函数 ==============

/**
 * 生成双色球号码
 * @param {Object} options - 生成选项
 * @param {string[]} options.lastRed - 上期红球
 * @param {string} options.lastBlue - 上期蓝球
 * @param {number} options.repeat - 重复上期红球数量
 * @param {number} options.consecutive - 连续号码组数
 * @param {number} options.sameTail - 同尾号组数
 * @param {boolean} options.excludeLastBlue - 是否排除上期蓝球
 */
export function generateLottery(options = {}) {
  const history = loadHistory();
  const historyCombos = buildHistoryCombos(history);

  const lastRed = options.lastRed || [];
  const lastBlue = options.lastBlue || '';

  const redBalls = generateRedBalls(historyCombos, {
    lastRed,
    repeat: options.repeat || 2,
    consecutive: options.consecutive || 1,
    sameTail: options.sameTail || 1,
  });

  if (!redBalls) {
    return { error: '无法生成符合条件的号码，请调整规则参数' };
  }

  const blueBall = generateBlueBall(
    options.excludeLastBlue !== false ? lastBlue : null,
    lastBlue
  );

  const result = { redBalls, blueBall };
  const validation = validate(result, lastRed, lastBlue);
  const output = formatOutput(result, validation, lastRed);

  return { result, validation, output };
}

// CLI 模式：直接运行脚本时执行
if (process.argv[1] && process.argv[1].includes('lottery-generator.mjs')) {
  const args = process.argv.slice(2);
  const options = {};

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--last-red' && args[i + 1]) {
      options.lastRed = args[i + 1].split(',').map((s) => s.trim());
      i++;
    } else if (args[i] === '--last-blue' && args[i + 1]) {
      options.lastBlue = args[i + 1].trim();
      i++;
    } else if (args[i] === '--repeat' && args[i + 1]) {
      options.repeat = parseInt(args[i + 1]);
      i++;
    } else if (args[i] === '--consecutive' && args[i + 1]) {
      options.consecutive = parseInt(args[i + 1]);
      i++;
    } else if (args[i] === '--same-tail' && args[i + 1]) {
      options.sameTail = parseInt(args[i + 1]);
      i++;
    }
  }

  const result = generateLottery(options);
  if (result.error) {
    console.error(result.error);
    process.exit(1);
  } else {
    console.log(result.output);
  }
}
