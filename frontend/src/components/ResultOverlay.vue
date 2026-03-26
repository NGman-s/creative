<template>
  <view class="overlay-container" :class="{ visible: visible }">
    <!-- Backdrop -->
    <view class="backdrop" @click="$emit('close')" v-if="visible"></view>

    <!-- Bottom Sheet -->
    <view class="bottom-sheet" :class="{ 'slide-up': visible, 'danger-border': (result?.total_traffic_light || '').toLowerCase() === 'red' }">
      <!-- Drag Handle -->
      <view class="sheet-handle-bar">
        <view class="sheet-handle"></view>
      </view>

      <!-- Loading State -->
      <view class="loading-state" v-if="loading">
        <view class="loading-spinner"></view>
        <text class="loading-text">正在分析...</text>
        <AIThoughtViewer
          :visible="true"
          :stage="stage"
          :healthConditions="healthConditions"
          :isEmbedded="true"
        />
      </view>

      <!-- Result Content -->
      <scroll-view scroll-y class="sheet-content" v-if="!loading && result">
        <!-- Header Section -->
        <view class="result-header">
          <view class="title-row">
            <text class="dish-name">{{ result.main_name || result.items?.[0]?.name || '识别结果' }}</text>
            <view class="traffic-badge" :class="trafficLight">
              {{ getTrafficLightLabel(trafficLight) }}
            </view>
          </view>

          <view class="header-content">
            <view class="header-summary">
              <view class="nutrition-hero">
                <view class="nutrition-item">
                  <view v-if="trafficLight === 'red'" class="danger-dot"></view>
                  <text class="nutri-value" :class="{ 'text-danger': trafficLight === 'red' }">
                    {{ nutritionTotals.calories_kcal }}
                  </text>
                  <text class="nutri-unit">kcal</text>
                  <text class="nutri-label">热量</text>
                  <text v-if="trafficLight === 'red'" class="warning-icon">⚠️</text>
                </view>
              </view>

              <view class="nutrition-tags">
                <text
                  v-for="tag in nutritionTags"
                  :key="tag"
                  class="tag-chip"
                >{{ tag }}</text>
                <text v-if="nutritionTags.length === 0" class="tag-chip muted">暂无标签</text>
              </view>
            </view>

            <view class="metrics-board">
              <view class="nutrition-compact-list">
                <view
                  v-for="metric in nutritionMetrics"
                  :key="metric.key"
                  class="compact-metric"
                >
                  <view class="compact-metric-badge" :class="metric.accent">{{ metric.label }}</view>
                  <view class="compact-metric-value-row">
                    <text class="compact-metric-value">{{ metric.displayValue }}</text>
                    <text class="compact-metric-unit">{{ metric.unit }}</text>
                  </view>
                </view>
              </view>
            </view>
          </view>

          <view v-if="riskFlags.length" class="risk-chip-row">
            <text
              v-for="flag in riskFlags"
              :key="`${flag.code}-${flag.severity}`"
              class="risk-chip"
              :class="flag.severity"
            >{{ getRiskLabel(flag.code) }}</text>
          </view>
        </view>

        <!-- Health Warning Section -->
        <view class="section-container" v-if="result.warning_message">
          <view class="warning-alert-card" :class="trafficLight">
            <text class="warning-icon-large">⚠️</text>
            <view class="warning-content">
              <view class="warning-title">健康预警</view>
              <text class="warning-text">{{ result.warning_message }}</text>
            </view>
          </view>
        </view>

        <!-- AI Analysis Section -->
        <view class="section-container">
          <view class="section-title">AI 分析</view>
          <view class="analysis-card">
            <view class="analysis-text summary">
              {{ result.total_analysis?.summary || '暂无分析摘要' }}
            </view>
            <view class="analysis-divider"></view>
            <view class="suggestion-row">
              <text class="suggestion-icon">💡</text>
              <text class="analysis-text suggestion">
                {{ result.total_analysis?.suggestion || '暂无建议' }}
              </text>
            </view>
          </view>
        </view>

        <!-- Thought Process (Expandable/Optional) -->
        <view class="section-container" v-if="result.thought_process">
          <view class="thought-card">
            <view class="thought-toggle" @click="toggleThought">
              <view class="thought-toggle-copy">
                <view class="section-title small compact">识别逻辑</view>
                <text class="thought-toggle-hint">
                  {{ isThoughtExpanded ? '点击收起' : '点击展开' }}
                </text>
              </view>
              <text
                class="thought-toggle-icon"
                :class="{ expanded: isThoughtExpanded }"
              >⌄</text>
            </view>
            <view v-if="isThoughtExpanded" class="thought-text">{{ result.thought_process }}</view>
          </view>
        </view>

        <!-- AI Hack Section (New) -->
        <view class="section-container" v-if="trafficLight !== 'green' || result.alternatives">
          <view class="section-title">AI 爆改建议</view>

          <!-- Generate Button -->
          <view v-if="!result.alternatives" class="hack-generate-box">
             <button
               class="btn-hack"
               :loading="loadingAlternatives"
               :disabled="loadingAlternatives"
               @click="handleHackClick"
             >
               <text>{{ loadingAlternatives ? '正在生成爆改方案...' : '点击获取 AI 爆改建议' }}</text>
             </button>
             <text class="hack-tip">💡 发现非绿灯食物，让 AI 为您提供更优选择</text>
          </view>

          <!-- Alternatives Display -->
          <view v-else class="alternatives-card">
            <view class="alt-item">
              <view class="alt-header">
                <text class="alt-icon">🍽️</text>
                <text class="alt-label">点餐更优选</text>
              </view>
              <text class="alt-text">{{ result.alternatives.ordering_hint }}</text>
            </view>
            <view class="alt-divider"></view>
            <view class="alt-item">
              <view class="alt-header">
                <text class="alt-icon">👨‍🍳</text>
                <text class="alt-label">自制健康改</text>
              </view>
              <text class="alt-text">{{ result.alternatives.cooking_hint }}</text>
            </view>
          </view>
        </view>

        <!-- Action Buttons -->
        <view class="action-area button-group">
          <button class="btn-secondary" @click="$emit('discard')">不保存</button>
          <button class="btn-primary" :class="{ 'btn-danger': trafficLight === 'red' }" @click="handleSave">
            {{ trafficLight === 'red' ? '仍要保存' : '保存并关闭' }}
          </button>
        </view>
      </scroll-view>
    </view>
  </view>
</template>

<script setup>
import { computed, defineProps, defineEmits, ref, watch } from 'vue';
import AIThoughtViewer from './AIThoughtViewer.vue';
import {
  NUTRITION_OVERVIEW_METRICS,
  formatNutritionValue,
  getNutritionTagsFromResult,
  getNutritionTotalsFromResult,
  getRiskFlagsFromResult
} from '@/utils/nutrition';

const props = defineProps({
  visible: Boolean,
  loading: Boolean,
  result: Object,
  stage: Number,
  healthConditions: Array,
  loadingAlternatives: Boolean
});

const emit = defineEmits(['close', 'save', 'discard', 'generate-alternatives']);
const isThoughtExpanded = ref(false);
const trafficLight = computed(() => {
  const color = String(props.result?.total_traffic_light || props.result?.items?.[0]?.traffic_light || 'yellow').toLowerCase();
  return ['green', 'yellow', 'red'].includes(color) ? color : 'yellow';
});
const nutritionTotals = computed(() => getNutritionTotalsFromResult(props.result || {}));
const nutritionTags = computed(() => getNutritionTagsFromResult(props.result || {}));
const riskFlags = computed(() => getRiskFlagsFromResult(props.result || {}));
const nutritionMetrics = computed(() =>
  NUTRITION_OVERVIEW_METRICS.map((metric) => ({
    ...metric,
    displayValue: formatNutritionValue(metric.key, nutritionTotals.value[metric.key])
  }))
);

const toggleThought = () => {
  if (!props.result?.thought_process) {
    return;
  }
  isThoughtExpanded.value = !isThoughtExpanded.value;
};

watch(
  () => [props.visible, props.loading, props.result?.thought_process],
  () => {
    isThoughtExpanded.value = false;
  }
);

const handleHackClick = () => {
  emit('generate-alternatives');
};

const handleSave = () => {
  emit('save');
};

const getTrafficLightLabel = (color) => {
  if (!color) return '未知';
  const c = color.toLowerCase();
  const map = {
    'green': '推荐',
    'yellow': '适量',
    'red': '少吃'
  };
  return map[c] || '未知';
};

const getRiskLabel = (code) => {
  const map = {
    high_calorie: '高热量',
    high_sugar: '高糖',
    high_sodium: '高钠',
    high_fat: '高脂',
    high_saturated_fat: '饱和脂肪高',
    low_protein: '低蛋白',
    low_fiber: '低纤维',
    allergen_risk: '过敏原风险',
    gluten_risk: '麸质风险',
    lactose_risk: '乳糖风险'
  };
  return map[code] || '营养风险';
};
</script>

<style lang="scss" scoped>
.overlay-container {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1000;
  pointer-events: none;
  visibility: hidden;
  transition: visibility 0.3s;

  &.visible {
    pointer-events: auto;
    visibility: visible;
  }
}

.backdrop {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(2px);
  opacity: 0;
  animation: fadeIn 0.3s forwards;
}

@keyframes fadeIn {
  to { opacity: 1; }
}

.bottom-sheet {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  background: #FFFFFF;
  border-radius: 20px 20px 0 0;
  box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.1);
  transform: translateY(100%);
  transition: transform 0.3s cubic-bezier(0.2, 0.8, 0.2, 1);
  display: flex;
  flex-direction: column;
  max-height: 85vh;
  padding-bottom: env(safe-area-inset-bottom);

  &.slide-up {
    transform: translateY(0);
  }

  &.danger-border {
    border: 2px solid #FF3B30;
    box-shadow: 0 -4px 30px rgba(255, 59, 48, 0.2);
  }
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
  width: 36px;
  height: 5px;
  background: #E5E5EA;
  border-radius: 3px;
}

/* Loading State */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
}

.loading-spinner {
  width: 30px;
  height: 30px;
  border: 3px solid #E5E5EA;
  border-top-color: #007AFF;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  font-size: 17px;
  font-weight: 600;
  color: #1D1D1F;
  margin-bottom: 8px;
}

.loading-sub {
  font-size: 13px;
  color: #86868B;
}

/* Result Content */
.sheet-content {
  flex: 1;
  width: 100%;
  overflow-y: auto;
}

.result-header {
  padding: 10px 24px 24px;
}

.title-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.dish-name {
  font-size: 28px;
  font-weight: 700;
  color: #1D1D1F;
  line-height: 1.2;
  flex: 1;
  margin-right: 12px;
}

.traffic-badge {
  padding: 6px 12px;
  border-radius: 100px;
  font-size: 13px;
  font-weight: 600;
  color: #FFF;
  flex-shrink: 0;

  &.green { background-color: #34C759; }
  &.yellow { background-color: #FF9500; }
  &.red { background-color: #FF3B30; }
}

.header-content {
  display: flex;
  align-items: flex-start;
  gap: 28px;
  margin-top: 10px;
}

.header-summary {
  flex: 0 0 320px;
  min-width: 0;
}

.nutrition-hero {
  display: flex;
  align-items: center;
  padding-top: 2px;
}

.nutrition-row {
  display: flex;
  align-items: center;
}

.nutrition-item {
  display: flex;
  align-items: baseline;
}

.nutri-value {
  font-size: 24px;
  font-weight: 700;
  color: #1D1D1F;
  margin-right: 2px;

  &.text-danger {
    color: #FF3B30;
  }
}

.danger-dot {
  width: 10px;
  height: 10px;
  background-color: #FF3B30;
  border-radius: 50%;
  margin-right: 8px;
  animation: pulse-red 1.5s infinite;
}

@keyframes pulse-red {
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(255, 59, 48, 0.7); }
  70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(255, 59, 48, 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(255, 59, 48, 0); }
}

.warning-icon {
  margin-left: 8px;
  font-size: 18px;
}

.nutri-unit {
  font-size: 13px;
  color: #86868B;
  margin-right: 6px;
}

.nutri-label {
  font-size: 13px;
  color: #86868B;
}

.nutrition-divider {
  width: 1px;
  height: 20px;
  background: #E5E5EA;
  margin: 0 16px;
}

.nutrition-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 18px;
}

.tag-chip {
  padding: 4px 10px;
  background: #F2F2F7;
  color: #636366;
  font-size: 12px;
  border-radius: 6px;
  font-weight: 500;
}

.tag-chip.muted {
  color: #8E8E93;
}

.metrics-board {
  flex: 1;
  min-width: 0;
  padding-top: 4px;
}

.nutrition-compact-list {
  display: grid;
  grid-template-columns: repeat(3, minmax(118px, 1fr));
  gap: 14px 22px;
  width: 100%;
  max-width: 760px;
}

.compact-metric {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 8px;
  min-width: 0;
}

.compact-metric-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 56px;
  padding: 5px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  color: #374151;
  background: #eef2f7;
}

.compact-metric-badge.protein {
  background: #e6f7ec;
  color: #1f7a3d;
}

.compact-metric-badge.fat {
  background: #fff0dc;
  color: #b45309;
}

.compact-metric-badge.carb {
  background: #efeaff;
  color: #5b21b6;
}

.compact-metric-badge.fiber {
  background: #e8f5ff;
  color: #0369a1;
}

.compact-metric-badge.sugar {
  background: #ffe7ee;
  color: #be185d;
}

.compact-metric-badge.sodium {
  background: #eef0f5;
  color: #4b5563;
}

.compact-metric-value-row {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.compact-metric-value {
  font-size: 16px;
  font-weight: 700;
  color: #111827;
}

.compact-metric-unit {
  font-size: 11px;
  color: #6b7280;
}

.risk-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
}

.risk-chip {
  padding: 5px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  background: #f3f4f6;
  color: #4b5563;
}

.risk-chip.low {
  background: #fff7e8;
  color: #9a6700;
}

.risk-chip.medium {
  background: #fff1db;
  color: #c05c00;
}

.risk-chip.high {
  background: #ffe6e6;
  color: #c62828;
}

@media (max-width: 720px) {
  .header-content {
    flex-direction: column;
    gap: 18px;
  }

  .header-summary {
    flex-basis: auto;
    width: 100%;
  }

  .metrics-board {
    width: 100%;
  }

  .nutrition-compact-list {
    grid-template-columns: repeat(2, 132px);
    gap: 10px 16px;
  }
}

@media (max-width: 420px) {
  .nutrition-compact-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

/* Analysis Section */
.section-container {
  padding: 0 24px 24px;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: #1D1D1F;
  margin-bottom: 12px;

  &.small {
    font-size: 13px;
    color: #86868B;
  }

  &.compact {
    margin-bottom: 0;
  }
}

.analysis-card {
  background: #F5F5F7;
  border-radius: 16px;
  padding: 16px;
}

/* Warning Alert Card */
.warning-alert-card {
  display: flex;
  padding: 16px;
  border-radius: 16px;
  margin-bottom: 8px;
  align-items: flex-start;

  &.red {
    background-color: #FFF2F2;
    border: 1px solid #FF3B30;
    .warning-icon-large { color: #FF3B30; }
    .warning-title { color: #FF3B30; }
  }

  &.yellow {
    background-color: #FFF9F2;
    border: 1px solid #FF9500;
    .warning-icon-large { color: #FF9500; }
    .warning-title { color: #FF9500; }
  }
}

.warning-icon-large {
  font-size: 24px;
  margin-right: 12px;
  margin-top: -2px;
}

.warning-content {
  flex: 1;
}

.warning-title {
  font-size: 16px;
  font-weight: 700;
  margin-bottom: 4px;
}

.warning-text {
  font-size: 14px;
  line-height: 1.4;
  color: #1D1D1F;
}

.analysis-text {
  font-size: 15px;
  line-height: 1.5;
  color: #1D1D1F;

  &.summary {
    font-weight: 500;
  }

  &.suggestion {
    color: #48484A;
  }
}

.analysis-divider {
  height: 1px;
  background: #E5E5EA;
  margin: 12px 0;
}

.suggestion-row {
  display: flex;
  align-items: flex-start;
}

.suggestion-icon {
  margin-right: 8px;
  font-size: 16px;
}

.thought-card {
  background: #F9F9F9;
  border-radius: 12px;
  overflow: hidden;
}

.thought-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
}

.thought-toggle-copy {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.thought-toggle-hint {
  font-size: 12px;
  color: #A1A1A6;
}

.thought-toggle-icon {
  font-size: 16px;
  color: #86868B;
  transform: rotate(0deg);
  transition: transform 0.2s ease;

  &.expanded {
    transform: rotate(180deg);
  }
}

.thought-text {
  font-size: 13px;
  line-height: 1.5;
  color: #86868B;
  padding: 0 12px 12px;
}

/* Action Area */
.action-area {
  padding: 0 24px 24px;
}

.button-group {
  display: flex;
  gap: 16px;
}

.btn-secondary {
  flex: 1;
  height: 50px;
  line-height: 50px;
  font-size: 17px;
  background-color: #F2F2F7;
  color: #007AFF;
  border-radius: 14px; /* Matches iOS default button radius often */
  font-weight: 600;
  border: none;

  &:active {
    opacity: 0.7;
    background-color: #E5E5EA;
  }
}

.btn-primary {
  flex: 2;
  height: 50px;
  line-height: 50px;
  font-size: 17px;
  border-radius: 14px;

  &.btn-danger {
    background-color: #FF3B30 !important;
    color: #FFF;
  }
}

/* AI Hack Section Styles */
.hack-generate-box {
  background: #F0F9EB;
  border: 1px dashed #67C23A;
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.btn-hack {
  width: 100%;
  height: 44px;
  line-height: 44px;
  background-color: #34C759;
  color: #FFF;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 600;
  display: flex;
  justify-content: center;
  align-items: center;
  border: none;

  &:active {
    opacity: 0.8;
  }

  &[disabled] {
    background-color: #A9E0B2;
    opacity: 1;
  }
}

.hack-loading-icon {
  margin-right: 8px;
  animation: spinner 2s linear infinite;
}

@keyframes spinner {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.hack-tip {
  font-size: 12px;
  color: #8E8E93;
}

.alternatives-card {
  background: linear-gradient(135deg, #F0F9EB 0%, #F5FFF0 100%);
  border: 1px solid #C2E7B0;
  border-radius: 16px;
  padding: 16px;
}

.alt-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.alt-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.alt-icon {
  font-size: 16px;
}

.alt-label {
  font-size: 14px;
  font-weight: 700;
  color: #34C759;
}

.alt-text {
  font-size: 14px;
  line-height: 1.5;
  color: #1D1D1F;
}

.alt-divider {
  height: 1px;
  background-color: #C2E7B0;
  margin: 12px 0;
}
</style>


