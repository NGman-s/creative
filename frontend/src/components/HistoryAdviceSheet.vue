<template>
  <view class="overlay-container" :class="{ visible }">
    <view v-if="visible" class="backdrop" @click="emit('close')"></view>

    <view class="bottom-sheet" :class="{ 'slide-up': visible }">
      <view class="sheet-handle-bar">
        <view class="sheet-handle"></view>
      </view>

      <scroll-view v-if="visible" scroll-y class="sheet-content">
        <view class="hero-card">
          <text class="hero-eyebrow">AI 饮食问答</text>
          <text class="hero-title">结合你的饮食记录，回答今天、最近或整体饮食问题</text>
          <text class="hero-copy">
            AI 会参考近几次记录、近 7 天趋势和你的健康目标来回答。
          </text>
        </view>

        <view class="section-container">
          <view class="section-header">
            <text class="section-title">输入问题</text>
            <text class="section-note">留空会使用默认问题</text>
          </view>

          <textarea
            class="question-input"
            :value="question"
            maxlength="120"
            auto-height
            placeholder="比如：今天吃得怎么样？"
            placeholder-class="question-placeholder"
            @input="handleInput"
          />

          <view class="question-toolbar">
            <text class="question-tip">支持直接问今天吃得怎么样、最近问题或增肌减脂</text>
            <text class="question-count">{{ questionLength }}/120</text>
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

        <view v-if="errorMessage" class="section-container">
          <view class="error-card">
            <text class="error-title">本次咨询失败</text>
            <text class="error-text">{{ errorMessage }}</text>
          </view>
        </view>

        <view v-if="loading" class="section-container">
          <view class="loading-card">
            <text class="loading-title">AI 正在整理你的饮食记录</text>
            <text class="loading-text">这会结合近 7 天趋势、最近餐食摘要和你的目标一起作答。</text>
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
            <text class="placeholder-title">还没有生成回答</text>
            <text class="placeholder-copy">
              可以直接问“今天吃得怎么样”“我最近饮食最大的短板是什么”或“接下来一餐怎么补蛋白”。
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

const handleInput = (event) => {
  emit('update:question', event?.detail?.value || '');
};
</script>

<style lang="scss" scoped>
.overlay-container {
  position: fixed;
  inset: 0;
  z-index: 1000;
  pointer-events: none;
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
  background:
    radial-gradient(circle at top right, rgba(76, 141, 255, 0.14), transparent 28%),
    linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  border-radius: 28px 28px 0 0;
  box-shadow: 0 -20px 48px rgba(15, 23, 42, 0.16);
  transform: translateY(100%);
  transition: transform 0.28s ease;
  overflow: hidden;
}

.bottom-sheet.slide-up {
  transform: translateY(0);
}

.sheet-handle-bar {
  display: flex;
  justify-content: center;
  padding: 10px 0 4px;
}

.sheet-handle {
  width: 52px;
  height: 5px;
  border-radius: 999px;
  background: rgba(17, 24, 39, 0.12);
}

.sheet-content {
  max-height: calc(86vh - 20px);
  padding: 10px 18px calc(env(safe-area-inset-bottom) + 18px);
  box-sizing: border-box;
}

.hero-card,
.answer-card,
.insight-card,
.placeholder-card,
.loading-card,
.error-card {
  border-radius: 20px;
  padding: 18px;
}

.hero-card {
  background: linear-gradient(135deg, #172033 0%, #23406d 100%);
  color: #fff;
}

.hero-eyebrow {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.12);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.4px;
}

.hero-title {
  display: block;
  margin-top: 12px;
  font-size: 20px;
  line-height: 1.4;
  font-weight: 700;
}

.hero-copy {
  display: block;
  margin-top: 8px;
  font-size: 13px;
  line-height: 1.7;
  color: rgba(255, 255, 255, 0.82);
}

.section-container {
  margin-top: 16px;
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
  color: #172033;
}

.section-note {
  font-size: 12px;
  color: #7b8796;
}

.question-input {
  width: 100%;
  min-height: 104px;
  padding: 16px;
  box-sizing: border-box;
  border-radius: 18px;
  background: #f4f7fb;
  color: #172033;
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
.placeholder-copy {
  color: #7b8796;
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
  margin-top: 14px;
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
  background:
    radial-gradient(circle at top right, rgba(79, 141, 255, 0.12), transparent 32%),
    #f6f9ff;
  border: 1px solid rgba(79, 141, 255, 0.14);
}

.answer-text {
  font-size: 15px;
  line-height: 1.8;
  color: #172033;
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
  background: rgba(36, 88, 255, 0.08);
  color: #2458ff;
  font-size: 12px;
  font-weight: 600;
}

.insight-card {
  margin-top: 12px;
  background: #fff;
  border: 1px solid #e9eef5;
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
  color: #172033;
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

.action-area {
  padding: 18px 0 2px;
}

.btn-close {
  background: #172033;
  color: #fff;
}
</style>
