<template>
  <view class="overlay-container" :class="{ visible }">
    <view v-if="visible" class="backdrop" @click="emit('close')"></view>

    <view class="bottom-sheet" :class="{ 'slide-up': visible }">
      <view class="sheet-handle-bar">
        <view class="sheet-handle"></view>
      </view>

      <scroll-view v-if="visible" scroll-y class="sheet-content">
        <view class="hero-card">
          <view class="hero-badge-row">
            <text class="hero-eyebrow">AI 饮食问答</text>
            <text class="hero-caption">结合历史记录回答</text>
          </view>
          <text class="hero-title">今天、最近和下一餐，都可以直接问</text>
          <text class="hero-copy">
            AI 会结合你的最近记录、近 7 天趋势和健康目标，给出更贴近实际的回答。
          </text>
          <view class="hero-pills">
            <view class="hero-pill">
              <text class="hero-pill-label">今天</text>
              <text class="hero-pill-copy">看当天搭配</text>
            </view>
            <view class="hero-pill">
              <text class="hero-pill-label">最近</text>
              <text class="hero-pill-copy">看连续变化</text>
            </view>
            <view class="hero-pill">
              <text class="hero-pill-label">下一餐</text>
              <text class="hero-pill-copy">给调整建议</text>
            </view>
          </view>
        </view>

        <view class="section-container">
          <view class="composer-card">
            <view class="section-header">
              <text class="section-title">把问题抛给 AI</text>
              <text class="section-note">留空会自动做一次总结</text>
            </view>

            <textarea
              class="question-input"
              :value="question"
              maxlength="120"
              auto-height
              placeholder="例如：今天这几餐搭配合理吗？"
              placeholder-class="question-placeholder"
              @input="handleInput"
            />

            <view class="question-toolbar">
              <text class="question-tip">问题越具体，回答通常越有针对性。</text>
              <text class="question-count">{{ questionLength }}/120</text>
            </view>

            <view class="example-panel">
              <view class="example-header">
                <text class="example-title">试试这些问法</text>
                <text class="example-note">点一下直接填入</text>
              </view>
              <view class="example-list">
                <view
                  v-for="item in exampleQuestions"
                  :key="item"
                  class="example-chip"
                  :class="{ active: question === item }"
                  @tap="applyExample(item)"
                >
                  <text class="example-chip-text">{{ item }}</text>
                </view>
              </view>
            </view>

            <button
              class="btn-submit"
              :loading="loading"
              :disabled="loading || !hasHistory"
              @click="emit('submit')"
            >
              {{ loading ? 'AI 分析中...' : result ? '重新询问 AI' : '开始询问 AI' }}
            </button>

            <text v-if="!hasHistory" class="inline-empty-tip">
              还没有可用饮食记录，先保存几餐再来询问 AI。
            </text>
          </view>
        </view>

        <view v-if="errorMessage" class="section-container">
          <view class="error-card">
            <text class="error-title">本次咨询失败</text>
            <text class="error-text">{{ errorMessage }}</text>
          </view>
        </view>

        <view v-if="loading" class="section-container">
          <view class="loading-card">
            <text class="loading-title">AI 正在整理你的饮食记录</text>
            <text class="loading-text">这会结合最近记录、近 7 天趋势和你的目标一起作答。</text>
          </view>
        </view>

        <view v-else-if="result" class="section-container">
          <view class="section-title">AI 回答</view>
          <view class="answer-card">
            <text class="answer-text">{{ result.answer }}</text>

            <view v-if="result.focus_tags?.length" class="focus-tags">
              <text
                v-for="tag in result.focus_tags"
                :key="tag"
                class="focus-tag"
              >{{ tag }}</text>
            </view>
          </view>

          <view v-if="result.observations?.length" class="insight-card">
            <view class="insight-header">
              <text class="insight-title">记录观察</text>
            </view>
            <view
              v-for="(item, index) in result.observations"
              :key="`observation-${index}`"
              class="insight-row"
            >
              <view class="insight-dot observation"></view>
              <text class="insight-text">{{ item }}</text>
            </view>
          </view>

          <view v-if="result.suggestions?.length" class="insight-card action">
            <view class="insight-header">
              <text class="insight-title">建议动作</text>
            </view>
            <view
              v-for="(item, index) in result.suggestions"
              :key="`suggestion-${index}`"
              class="insight-row"
            >
              <view class="insight-dot suggestion"></view>
              <text class="insight-text">{{ item }}</text>
            </view>
          </view>
        </view>

        <view v-else class="section-container">
          <view class="placeholder-card">
            <text class="placeholder-title">先选一个问题开始</text>
            <text class="placeholder-copy">
              例如“今天这几餐搭配合理吗？”“最近哪一餐最容易超标？”或“如果今晚点外卖，怎么选更稳妥？”
            </text>
          </view>
        </view>

        <view class="action-area">
          <button class="btn-close" @click="emit('close')">关闭</button>
        </view>
      </scroll-view>
    </view>
  </view>
</template>

<script setup>
import { computed, defineEmits, defineProps } from 'vue';

const props = defineProps({
  visible: Boolean,
  question: {
    type: String,
    default: ''
  },
  loading: Boolean,
  errorMessage: {
    type: String,
    default: ''
  },
  hasHistory: Boolean,
  result: {
    type: Object,
    default: null
  }
});

const emit = defineEmits(['close', 'submit', 'update:question']);
const questionLength = computed(() => String(props.question || '').length);
const exampleQuestions = [
  '今天这几餐搭配合理吗？',
  '我最近最需要先改掉哪一个习惯？',
  '如果想减脂，下一餐怎么吃更稳妥？',
  '晚上容易饿，应该怎么调整？'
];

const handleInput = (event) => {
  emit('update:question', event?.detail?.value || '');
};

const applyExample = (question) => {
  if (props.loading) {
    return;
  }

  emit('update:question', question);
};
</script>

<style lang="scss" scoped>
.overlay-container {
  position: fixed;
  inset: 0;
  z-index: 1000;
  pointer-events: none;
  --text-primary: #172033;
  --text-secondary: #7b8796;
  --card-bg: #f4f7fb;
  --card-border: #e4ebf3;
  --soft-bg: #f9fafc;
  --line: #dde3eb;
  --accent: #2458ff;
  --accent-soft: rgba(36, 88, 255, 0.08);
}

.overlay-container.visible {
  pointer-events: auto;
}

.backdrop {
  position: absolute;
  inset: 0;
  background: rgba(15, 23, 42, 0.38);
  backdrop-filter: blur(6px);
}

.bottom-sheet {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  max-height: 86vh;
  background: linear-gradient(180deg, #ffffff 0%, #f9fafc 100%);
  border-radius: 24px 24px 0 0;
  box-shadow: 0 -12px 40px rgba(15, 23, 42, 0.14);
  transform: translate3d(0, 100%, 0);
  transition: transform 0.3s cubic-bezier(0.2, 0.8, 0.2, 1);
  overflow: hidden;
  padding-bottom: env(safe-area-inset-bottom);
  will-change: transform;
}

.bottom-sheet.slide-up {
  transform: translate3d(0, 0, 0);
}

.sheet-handle-bar {
  width: 100%;
  height: 24px;
  display: flex;
  justify-content: center;
  align-items: center;
  flex-shrink: 0;
}

.sheet-handle {
  width: 40px;
  height: 5px;
  border-radius: 999px;
  background: #d6dae1;
}

.sheet-content {
  max-height: calc(86vh - 24px);
  padding: 8px 24px 24px;
  box-sizing: border-box;
}

.hero-card,
.composer-card,
.answer-card,
.insight-card,
.placeholder-card,
.loading-card,
.error-card {
  border-radius: 20px;
  padding: 18px;
}

.hero-card {
  background:
    radial-gradient(circle at top left, rgba(255, 255, 255, 0.9), transparent 40%),
    linear-gradient(135deg, #eef4fb 0%, #f7f9fc 100%);
  border: 1px solid var(--card-border);
}

.hero-badge-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.hero-caption {
  font-size: 12px;
  color: var(--text-secondary);
}

.hero-eyebrow {
  display: inline-flex;
  align-items: center;
  padding: 5px 10px;
  border-radius: 999px;
  background: #fff;
  color: var(--accent);
  font-size: 12px;
  font-weight: 600;
  border: 1px solid #dbe8ff;
}

.hero-title {
  display: block;
  margin-top: 14px;
  font-size: 20px;
  line-height: 1.4;
  font-weight: 700;
  color: var(--text-primary);
}

.hero-copy {
  display: block;
  margin-top: 8px;
  font-size: 13px;
  line-height: 1.7;
  color: var(--text-secondary);
}

.hero-pills {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-top: 16px;
}

.hero-pill {
  padding: 12px;
  border-radius: 16px;
  background: #ffffff;
  border: 1px solid #e6edf5;
}

.hero-pill-label,
.hero-pill-copy {
  display: block;
}

.hero-pill-label {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-primary);
}

.hero-pill-copy {
  margin-top: 4px;
  font-size: 11px;
  color: var(--text-secondary);
}

.section-container {
  margin-top: 18px;
}

.composer-card,
.answer-card,
.insight-card,
.placeholder-card,
.loading-card,
.error-card {
  background: transparent;
  border: none;
  box-shadow: none;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 10px;
}

.section-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}

.section-note {
  font-size: 12px;
  color: var(--text-secondary);
}

.question-input {
  width: 100%;
  min-height: 104px;
  padding: 16px;
  box-sizing: border-box;
  border-radius: 18px;
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  color: var(--text-primary);
  font-size: 15px;
  line-height: 1.6;
}

.question-placeholder {
  color: #9aa6b2;
}

.question-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-top: 10px;
}

.question-tip,
.question-count,
.inline-empty-tip,
.example-note,
.loading-text,
.error-text,
.placeholder-copy,
.insight-text {
  font-size: 13px;
  line-height: 1.7;
}

.question-tip,
.question-count,
.inline-empty-tip,
.example-note,
.placeholder-copy {
  color: var(--text-secondary);
}

.example-panel {
  margin-top: 14px;
  padding: 14px;
  border-radius: 18px;
  background: #f9fafc;
  border: 1px solid #edf1f5;
}

.example-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.example-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
}

.example-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 12px;
}

.example-chip {
  max-width: 100%;
  padding: 10px 12px;
  border-radius: 14px;
  background: #ffffff;
  border: 1px solid #e4ebf3;
  transition: transform 0.16s ease, background 0.16s ease, border-color 0.16s ease;

  &:active {
    transform: scale(0.98);
  }
}

.example-chip.active {
  background: #eef4ff;
  border-color: #cfe0ff;
}

.example-chip-text {
  display: block;
  font-size: 13px;
  line-height: 1.5;
  color: var(--text-primary);
}

.btn-submit,
.btn-close {
  height: 50px;
  line-height: 50px;
  border: none;
  border-radius: 16px;
  font-size: 15px;
  font-weight: 700;
}

.btn-submit::after,
.btn-close::after {
  border: none;
}

.btn-submit {
  margin-top: 16px;
  background: linear-gradient(135deg, #2458ff 0%, #4f8dff 100%);
  color: #fff;
  box-shadow: 0 12px 24px rgba(36, 88, 255, 0.18);
}

.btn-submit[disabled] {
  background: #cfd8e3;
  color: rgba(255, 255, 255, 0.78);
  box-shadow: none;
}

.inline-empty-tip {
  display: block;
  margin-top: 10px;
}

.answer-card {
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  box-shadow: none;
}

.answer-text {
  font-size: 15px;
  line-height: 1.8;
  color: var(--text-primary);
}

.focus-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
}

.focus-tag {
  padding: 6px 12px;
  border-radius: 999px;
  background: var(--accent-soft);
  color: var(--accent);
  font-size: 12px;
  font-weight: 600;
}

.insight-card {
  margin-top: 12px;
  background: #ffffff;
  border: 1px solid #e9eef5;
  box-shadow: none;
}

.insight-card.action {
  background: linear-gradient(180deg, #fffdf7 0%, #ffffff 100%);
}

.insight-header {
  margin-bottom: 8px;
}

.insight-title,
.loading-title,
.error-title,
.placeholder-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
}

.insight-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding-top: 10px;
}

.insight-row:first-of-type {
  padding-top: 0;
}

.insight-dot {
  width: 8px;
  height: 8px;
  margin-top: 7px;
  border-radius: 999px;
  flex-shrink: 0;
}

.insight-dot.observation {
  background: #4f8dff;
}

.insight-dot.suggestion {
  background: #ff9f0a;
}

.placeholder-card,
.loading-card {
  background: #f4f7fb;
  border: none;
}

.loading-text,
.error-text,
.placeholder-copy {
  display: block;
  margin-top: 8px;
}

.error-card {
  background: #fff7f5;
  border: 1px solid rgba(255, 107, 107, 0.18);
}

.error-title {
  color: var(--text-primary);
}

.action-area {
  padding: 18px 0 2px;
}

.btn-close {
  background: #172033;
  color: #fff;
  border: none;
}
</style>
