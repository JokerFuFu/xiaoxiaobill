<template>
  <!-- 年度消费故事：入口卡片 + 时光机 Modal -->
  <div class="analysis-card story-entry-card" @click="showStoryModeFunc">
    <div class="story-card-content">
      <div class="story-icon">
        <i class="fas fa-film"></i>
      </div>
      <div class="story-title">年度消费故事</div>
      <div class="story-desc">点击开启您的时光之旅</div>
      <div class="story-btn">立即播放</div>
    </div>
  </div>

  <!-- 时光机 Modal -->
  <div v-if="showStoryMode" class="story-modal" @click.self="showStoryMode = false" style="display: flex;">
    <div class="story-content">
      <button class="close-story" @click="showStoryMode = false">
        <i class="fas fa-times"></i>
      </button>
      <div class="story-slides" ref="storySlides">
        <!-- 动态生成幻灯片 -->
      </div>
      <div class="story-controls">
        <button class="story-btn prev" @click="prevSlide">
          <i class="fas fa-chevron-left"></i>
        </button>
        <div class="story-indicators" ref="storyIndicators"></div>
        <button class="story-btn next" @click="nextSlide">
          <i class="fas fa-chevron-right"></i>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { buildStorySlides } from './storySlides'

const props = defineProps({
  // 年度故事数据
  storyData: {
    type: Object,
    default: null,
  },
})

const showStoryMode = ref(false)
const currentSlide = ref(0)
const storySlides = ref(null)
const storyIndicators = ref(null)

// 故事模式相关
let totalSlides = 0

function prevSlide() {
  if (currentSlide.value > 0) {
    currentSlide.value--
    updateSlidePosition()
  }
}

function nextSlide() {
  if (currentSlide.value < totalSlides - 1) {
    currentSlide.value++
    updateSlidePosition()
  }
}

function updateSlidePosition() {
  const slides = storySlides.value
  if (slides) {
    const allSlides = slides.querySelectorAll('.slide')
    allSlides.forEach((slide, index) => {
      slide.classList.toggle('active', index === currentSlide.value)
    })
    updateIndicators()
  }
}

function updateIndicators() {
  const indicators = storyIndicators.value
  if (indicators) {
    Array.from(indicators.children).forEach((dot, index) => {
      dot.classList.toggle('active', index === currentSlide.value)
    })
  }
}

async function showStoryModeFunc() {
  const data = props.storyData
  if (!data) {
    console.warn('[Story] No story data available')
    return
  }

  currentSlide.value = 0
  showStoryMode.value = true

  // 等待 DOM 更新后再生成幻灯片
  await nextTick()
  generateStorySlides()
}

function generateStorySlides() {
  const data = props.storyData
  console.log('[Story] generateStorySlides called, data:', data)

  if (!data) {
    console.warn('[Story] No data available')
    return
  }

  const slides = storySlides.value
  const indicators = storyIndicators.value

  console.log('[Story] slides element:', slides)
  console.log('[Story] indicators element:', indicators)

  if (!slides || !indicators) {
    console.warn('[Story] DOM elements not found')
    return
  }

  // 生成幻灯片（与老前端保持一致的模板）
  const slideTemplates = buildStorySlides(data)

  totalSlides = slideTemplates.length

  // 设置幻灯片内容
  slides.innerHTML = slideTemplates.join('')

  // 生成指示器
  indicators.innerHTML = slideTemplates.map((_, i) =>
    `<span class="indicator ${i === 0 ? 'active' : ''}" data-slide-index="${i}"></span>`
  ).join('')

  // 更新幻灯片位置
  updateSlidePosition()
}
</script>

<style scoped>
.analysis-card {
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow-card);
}

/* 年度故事卡片 */
.story-entry-card {
  width: 280px;
  flex-shrink: 0;
  height: 100%;
  margin-bottom: 0 !important;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: transform 0.2s ease;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.story-entry-card:hover {
  transform: translateY(-2px);
}

.story-card-content {
  text-align: center;
}

.story-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.story-title {
  font-size: 24px;
  font-weight: 600;
  margin-bottom: 8px;
}

.story-desc {
  font-size: 14px;
  opacity: 0.9;
  margin-bottom: 20px;
}

.story-btn {
  padding: 8px 24px;
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.4);
  border-radius: 20px;
  font-size: 14px;
}

/* 故事 Modal */
.story-modal {
  display: none;
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.3);
  z-index: 9999;
  justify-content: center;
  align-items: center;
  -webkit-backdrop-filter: blur(20px);
  backdrop-filter: blur(20px);
  transition: all 0.3s ease;
}

.story-content {
  width: 100%;
  max-width: 420px;
  height: 75vh;
  min-height: 500px;
  position: relative;
  color: #333;
  display: flex;
  flex-direction: column;
}

.close-story {
  position: absolute;
  top: -50px;
  right: 0;
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  width: 40px;
  height: 40px;
  color: white;
  font-size: 20px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  z-index: 10;
}

.close-story:hover {
  background: rgba(255, 255, 255, 0.4);
  transform: rotate(90deg);
}

.story-slides {
  flex: 1;
  position: relative;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.95);
  border-radius: var(--radius-xl);
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(255, 255, 255, 1);
}

.slide {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
  transition: opacity 0.5s ease, transform 0.5s ease;
  transform: scale(0.9);
  display: flex;
  justify-content: center;
  align-items: center;
  text-align: center;
  padding: 40px;
  pointer-events: none;
}

.slide.active {
  opacity: 1;
  transform: scale(1);
  pointer-events: auto;
}

.slide-number {
  font-size: 48px;
  font-weight: 600;
  color: var(--border-color);
  margin-bottom: 20px;
}

.slide-title {
  font-size: 28px;
  font-weight: 600;
  color: var(--text-color);
  margin-bottom: 16px;
}

.slide-content {
  font-size: 18px;
  color: var(--secondary-text);
  line-height: 1.6;
  max-width: 600px;
}

.slide-content h1 {
  font-size: 28px;
  margin-bottom: 20px;
  color: #1d1d1f;
  font-weight: 800;
}

.slide-content h2 {
  font-size: 24px;
  margin-bottom: 30px;
  color: #1d1d1f;
  font-weight: 700;
}

.slide-content p {
  margin-bottom: 12px;
  color: var(--secondary-text);
}

.slide-date {
  font-size: 18px;
  color: #86868b;
  margin-bottom: 10px;
  font-weight: 500;
}

.slide-amount {
  font-size: 40px;
  font-weight: 800;
  background: linear-gradient(135deg, #FF9500 0%, #FF3B30 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-bottom: 20px;
  font-family: var(--font-family-mono);
}

.slide-keyword {
  font-size: 36px;
  font-weight: 800;
  color: #007AFF;
  margin-bottom: 20px;
}

.slide-big-icon {
  font-size: 80px;
  color: rgba(0, 0, 0, 0.05);
  margin-top: 40px;
}

.story-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 0;
}

/* 翻页按钮样式 - 使用更具体的选择器避免覆盖卡片中的按钮 */
.story-controls .story-btn {
  background: none;
  border: none;
  color: white !important;
  font-size: 24px;
  cursor: pointer;
  opacity: 0.7;
  transition: opacity 0.2s;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.story-controls .story-btn:hover {
  opacity: 1;
}

.story-indicators {
  display: flex;
  gap: 8px;
}

.indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.3);
  cursor: pointer;
  transition: all 0.2s ease;
}

.indicator.active {
  background: white;
  transform: scale(1.2);
}

@media (max-width: 1200px) {
  .story-entry-card {
    width: 100%;
    height: 200px;
  }
}
</style>
