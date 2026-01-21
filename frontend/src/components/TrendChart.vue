<template>
  <view class="chart-container">
    <view class="chart-header">
      <text class="chart-title">本周热量趋势</text>
      <text class="chart-subtitle">平均: {{ averageCalories }} kcal</text>
    </view>

    <view class="chart-body">
      <!-- Grid Lines -->
      <view class="grid-line" style="top: 0%"></view>
      <view class="grid-line" style="top: 50%"></view>
      <view class="grid-line" style="top: 100%"></view>

      <!-- Bars -->
      <view class="bars-container">
        <view v-for="(item, index) in normalizedData" :key="index" class="bar-group">
          <view class="bar-wrapper">
             <view
               class="bar"
               :style="{ height: item.height + '%' }"
               :class="{ 'bar-active': item.calories > 0 }"
             ></view>
          </view>
          <text class="bar-label">{{ item.label }}</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, defineProps } from 'vue';

const props = defineProps({
  data: {
    type: Array,
    default: () => []
  }
});

const averageCalories = computed(() => {
  if (!props.data || props.data.length === 0) return 0;
  const sum = props.data.reduce((acc, curr) => acc + curr.calories, 0);
  return Math.round(sum / props.data.length);
});

const normalizedData = computed(() => {
  if (!props.data || props.data.length === 0) return [];

  // Find max value for scaling (min 2500 for visual consistency)
  const maxCalories = Math.max(2500, ...props.data.map(d => d.calories));

  return props.data.map(d => ({
    ...d,
    height: Math.min(100, (d.calories / maxCalories) * 100)
  }));
});
</script>

<style lang="scss" scoped>
.chart-container {
  background: transparent;
  padding: 0;
  width: 100%;
}

.chart-header {
  margin-bottom: 24px;
}

.chart-title {
  font-size: 18px;
  font-weight: 600;
  color: #1d1d1f;
  margin-bottom: 4px;
  display: block;
}

.chart-subtitle {
  font-size: 13px;
  color: #86868b;
  font-weight: 500;
}

.chart-body {
  position: relative;
  height: 180px;
  width: 100%;
}

.grid-line {
  position: absolute;
  left: 0;
  width: 100%;
  height: 1px;
  background: #E5E5EA; /* Light gray separator */
  border-bottom: 1px dashed transparent; /* Optional styling */
  z-index: 1;
}

.bars-container {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  height: 100%;
  position: relative;
  z-index: 2;
  padding-bottom: 20px; /* Space for labels */
}

.bar-group {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  height: 100%;
  justify-content: flex-end;
}

.bar-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  align-items: center;
  width: 100%;
  padding-bottom: 8px;
}

.bar {
  width: 8px;
  background: #F2F2F7; /* Inactive color */
  border-radius: 4px;
  transition: height 0.6s cubic-bezier(0.2, 0.8, 0.2, 1);
  min-height: 4px;
}

.bar-active {
  background: #007AFF; /* Apple Blue */
}

.bar-label {
  color: #86868b;
  font-size: 11px;
  font-weight: 500;
  position: absolute;
  bottom: 0;
}
</style>
