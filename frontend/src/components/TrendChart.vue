<template>
  <view class="chart-container">
    <view class="chart-header">
      <text class="chart-title">本周热量趋势 (Weekly Calories)</text>
      <view class="chart-legend">
        <view class="legend-dot"></view>
        <text class="legend-text">kcal</text>
      </view>
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
             <view class="bar-value" v-if="item.calories > 0">{{ item.calories }}</view>
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

    <!-- Decorative HUD corners -->
    <view class="corner top-left"></view>
    <view class="corner top-right"></view>
    <view class="corner bottom-left"></view>
    <view class="corner bottom-right"></view>
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

const normalizedData = computed(() => {
  if (!props.data || props.data.length === 0) return [];

  // Find max value for scaling (min 2000 to avoid huge bars for small values)
  const maxCalories = Math.max(2500, ...props.data.map(d => d.calories));

  return props.data.map(d => ({
    ...d,
    height: Math.min(100, (d.calories / maxCalories) * 100)
  }));
});
</script>

<style scoped>
.chart-container {
  position: relative;
  background: rgba(0, 20, 30, 0.6);
  border: 1px solid rgba(0, 243, 255, 0.3);
  padding: 20px;
  margin-bottom: 20px;
  font-family: 'Courier New', Courier, monospace;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  border-bottom: 1px solid rgba(0, 243, 255, 0.2);
  padding-bottom: 10px;
}

.chart-title {
  color: #00f3ff;
  font-size: 14px;
  font-weight: bold;
  letter-spacing: 1px;
}

.chart-legend {
  display: flex;
  align-items: center;
}

.legend-dot {
  width: 8px;
  height: 8px;
  background: #00f3ff;
  margin-right: 5px;
  box-shadow: 0 0 5px #00f3ff;
}

.legend-text {
  color: rgba(0, 243, 255, 0.7);
  font-size: 10px;
}

.chart-body {
  position: relative;
  height: 150px;
  width: 100%;
}

.grid-line {
  position: absolute;
  left: 0;
  width: 100%;
  height: 1px;
  background: rgba(0, 243, 255, 0.1);
  z-index: 1;
}

.bars-container {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  height: 100%;
  position: relative;
  z-index: 2;
  padding-top: 20px; /* Space for values */
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
  padding-bottom: 5px;
}

.bar {
  width: 12px;
  background: rgba(0, 243, 255, 0.2);
  border: 1px solid rgba(0, 243, 255, 0.5);
  transition: height 1s ease-out;
  position: relative;
}

.bar-active {
  background: linear-gradient(to top, rgba(0, 243, 255, 0.2), rgba(0, 243, 255, 0.8));
  box-shadow: 0 0 10px rgba(0, 243, 255, 0.3);
}

.bar-value {
  color: #fff;
  font-size: 8px;
  margin-bottom: 2px;
  transform: scale(0.8);
}

.bar-label {
  color: rgba(0, 243, 255, 0.7);
  font-size: 8px;
  margin-top: 5px;
}

/* Corner decorations */
.corner {
  position: absolute;
  width: 10px;
  height: 10px;
  border: 2px solid #00f3ff;
  opacity: 0.8;
}

.top-left { top: -1px; left: -1px; border-right: none; border-bottom: none; }
.top-right { top: -1px; right: -1px; border-left: none; border-bottom: none; }
.bottom-left { bottom: -1px; left: -1px; border-right: none; border-top: none; }
.bottom-right { bottom: -1px; right: -1px; border-left: none; border-top: none; }
</style>
