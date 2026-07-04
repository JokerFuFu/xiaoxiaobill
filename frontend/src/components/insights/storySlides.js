// 年度消费故事幻灯片模板生成（与老前端保持一致）
import { formatMoney } from '@/utils/format'

/**
 * 根据故事数据构建幻灯片 HTML 模板数组
 * @param {Object} data - story_data 数据
 * @returns {string[]} 已过滤空串的幻灯片 HTML 数组
 */
export function buildStorySlides(data) {
  const slideTemplates = [
    // 1. 封面
    `
    <div class="slide active">
      <div class="slide-content">
        <h1>您的年度消费故事</h1>
        <p>这一年，您经历了 ${data.summary.total_days} 个日夜</p>
        <p>完成了 ${data.summary.tx_count} 笔交易</p>
        <div class="slide-big-icon"><i class="fas fa-book-open"></i></div>
      </div>
    </div>
    `,
    // 2. 年度首单
    (data.features && data.features.first_tx) ? `
    <div class="slide">
      <div class="slide-content">
        <h2>🎬 故事的开始</h2>
        <div class="slide-date">${data.features.first_tx.date}</div>
        <p>您在 <strong>${data.features.first_tx.merchant}</strong></p>
        <div class="slide-amount">¥${formatMoney(data.features.first_tx.amount)}</div>
        <p>用这笔消费开启了全新的一年。</p>
        <div class="slide-big-icon"><i class="fas fa-play-circle"></i></div>
      </div>
    </div>
    ` : '',
    // 3. 黄金时间
    (data.features && data.features.peak_hour !== undefined) ? `
    <div class="slide">
      <div class="slide-content">
        <h2>⏰ 剁手黄金点</h2>
        <p>每天的 <strong>${data.features.peak_hour}点</strong></p>
        <div class="slide-keyword" style="font-size:32px">是您最活跃的时刻</div>
        <p>${data.features.peak_hour < 12 ? '早起的鸟儿有虫吃？' : (data.features.peak_hour > 20 ? '月黑风高夜，正是剁手时。' : '工作日摸鱼下单？')}</p>
        <div class="slide-big-icon"><i class="fas fa-clock"></i></div>
      </div>
    </div>
    ` : '',
    // 4. 外卖之王
    (data.features && data.features.takeout && data.features.takeout.count > 5) ? `
    <div class="slide">
      <div class="slide-content">
        <h2>🥡 外卖品鉴家</h2>
        <div class="slide-amount">${data.features.takeout.count} 单</div>
        <p>贡献了 ${formatMoney(data.features.takeout.amount)} 元给外卖/快餐</p>
        <p>世界那么大，还是外卖最懂你的胃。</p>
        <div class="slide-big-icon"><i class="fas fa-utensils"></i></div>
      </div>
    </div>
    ` : '',
    // 5. 季节限定
    (data.features && data.features.top_season) ? `
    <div class="slide">
      <div class="slide-content">
        <h2>🍂 季节限定记忆</h2>
        <p>您在</p>
        <div class="slide-keyword" style="color:#FF7950">${data.features.top_season}天</div>
        <p>留下了最多的消费足迹。</p>
        <div class="slide-big-icon"><i class="fas ${data.features.top_season === '冬' ? 'fa-snowflake' : (data.features.top_season === '夏' ? 'fa-sun' : 'fa-leaf')}"></i></div>
      </div>
    </div>
    ` : '',
    // 6. 咖啡/奶茶指数
    (data.features && data.features.coffee && data.features.coffee.count > 0) ? `
    <div class="slide">
      <div class="slide-content">
        <h2>☕️ 续命指数</h2>
        <div class="slide-amount">${data.features.coffee.count} 杯</div>
        <p>您今年在咖啡/奶茶上投入了</p>
        <div class="slide-keyword" style="font-size:24px">¥${formatMoney(data.features.coffee.amount)}</div>
        <p>${data.features.coffee.count > 100 ? '相当于喝掉了一个浴缸的量！' : '您是理性的咖啡因摄入者。'}</p>
        <div class="slide-big-icon"><i class="fas fa-coffee"></i></div>
      </div>
    </div>
    ` : '',
    // 7. 深夜哲学
    (data.features && data.features.night && data.features.night.count > 0) ? `
    <div class="slide">
      <div class="slide-content">
        <h2>🌙 深夜哲学</h2>
        <p>晚10点后，您平均消费</p>
        <div class="slide-amount">¥${formatMoney(data.features.night.avg)}</div>
        <p>看来深夜不仅有灵感，还有食欲。</p>
        <div class="slide-big-icon"><i class="fas fa-moon"></i></div>
      </div>
    </div>
    ` : '',
    // 8. 周末人格
    (data.features && data.features.weekend) ? `
    <div class="slide">
      <div class="slide-content">
        <h2>🎭 周末人格</h2>
        <p>工作日均价 vs 周末均价</p>
        <div class="slide-amount" style="font-size:32px">¥${formatMoney(data.features.weekend.weekday_avg)} <span style="font-size:20px;color:#999">vs</span> ¥${formatMoney(data.features.weekend.weekend_avg)}</div>
        <p>${data.features.weekend.weekend_avg > data.features.weekend.weekday_avg * 2 ? '平日沙县小吃，周末米其林大餐！' : '您的消费习惯非常稳定。'}</p>
        <div class="slide-big-icon"><i class="fas fa-mask"></i></div>
      </div>
    </div>
    ` : '',
    // 9. 通胀感知
    (data.features && data.features.inflation && data.features.inflation.trend !== 'stable') ? `
    <div class="slide">
      <div class="slide-content">
        <h2>📈 通胀感知</h2>
        <p>您常去的 <strong>${data.features.inflation.merchant}</strong></p>
        <div class="slide-amount" style="font-size:32px">¥${formatMoney(data.features.inflation.start_price)} ➔ ¥${formatMoney(data.features.inflation.end_price)}</div>
        <p>${data.features.inflation.trend === 'up' ? '悄悄涨价了，且喝且珍惜。' : '居然降价了？良心商家！'}</p>
        <div class="slide-big-icon"><i class="fas fa-chart-line"></i></div>
      </div>
    </div>
    ` : '',
    // 10. 最贵的一天
    `
    <div class="slide">
      <div class="slide-content">
        <h2>💸 最"壕"的一天</h2>
        <div class="slide-date">${data.max_day.date}</div>
        <div class="slide-amount">${formatMoney(data.max_day.amount)}</div>
        <p>那天发生了什么？是爱自己多一点吗？</p>
        <div class="slide-big-icon"><i class="fas fa-shopping-bag"></i></div>
      </div>
    </div>
    `,
    // 11. 总结
    `
    <div class="slide">
      <div class="slide-content">
        <h2>✨ 年度关键词</h2>
        <div class="slide-keyword">${data.top_category.name}</div>
        <p>这是您投入最多的领域 (${formatMoney(data.top_category.amount)})</p>
        <p>新的一年，愿每一笔消费都物超所值！</p>
        <div class="slide-big-icon"><i class="fas fa-star"></i></div>
      </div>
    </div>
    `
  ].filter(Boolean) // 过滤掉空字符串（条件为false的幻灯片）

  return slideTemplates
}
