<template>
  <view class="chart-container">
    <view class="chart-header">
      <view>
        <text class="chart-title">本周{{ selectedMetric.label }}趋势</text>
        <text class="chart-subtitle">平均: {{ averageLabel }}</text>
      </view>
      <view class="metric-tabs">
        <view
          v-for="metric in metrics"
          :key="metric.key"
          class="metric-chip"
          :class="{ active: metric.key === selectedMetric.key }"
          :style="metric.key === selectedMetric.key ? activeChipStyle(metric) : {}"
          @tap="selectedMetricKey = metric.key"
        >
          {{ metric.label }}
        </view>
      </view>
    </view>

    <view class="chart-body">
      <view class="grid-line" style="top: 0%"></view>
      <view class="grid-line" style="top: 50%"></view>
      <view class="grid-line" style="top: 100%"></view>

      <view class="bars-container">
        <view v-for="(item, index) in normalizedData" :key="index" class="bar-group">
          <view class="bar-wrapper">
            <view
              class="bar"
              :style="barStyle(item)"
              :class="{ 'bar-active': item.value > 0 }"
            ></view>
          </view>
          <text class="bar-value">{{ item.valueLabel }}</text>
          <text class="bar-label">{{ item.label }}</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, defineProps, ref } from 'vue';
import { TREND_METRICS } from '@/utils/nutrition';

const props = defineProps({
  data: {
    type: Array,
    default: () => []
  }
});

const metrics = TREND_METRICS;
const selectedMetricKey = ref(metrics[0].key);

const selectedMetric = computed(() =>
  metrics.find((metric) => metric.key === selectedMetricKey.value) || metrics[0]
);

const formatTrendValue = (metric, value) => {
  const numericValue = Number(value || 0);
  if (metric.key === 'calories') {
    return `${Math.round(numericValue)} ${metric.unit}`;
  }
  const normalized = Number(numericValue.toFixed(1));
  return `${Number.isInteger(normalized) ? normalized : normalized.toFixed(1)} ${metric.unit}`;
};

const averageLabel = computed(() => {
  if (!props.data || props.data.length === 0) return `0 ${selectedMetric.value.unit}`;
  const total = props.data.reduce((sum, item) => sum + Number(item[selectedMetric.value.key] || 0), 0);
  return formatTrendValue(selectedMetric.value, total / props.data.length);
});

const normalizedData = computed(() => {
  if (!props.data || props.data.length === 0) return [];

  const metric = selectedMetric.value;
  const maxValue = Math.max(metric.maxFloor, ...props.data.map((item) => Number(item[metric.key] || 0)));

  return props.data.map((item) => {
    const value = Number(item[metric.key] || 0);
    return {
      ...item,
      value,
      valueLabel: metric.key === 'calories' ? `${Math.round(value)}` : `${Number(value.toFixed(1))}`,
      height: Math.min(100, (value / maxValue) * 100)
    };
  });
});

const activeChipStyle = (metric) => ({
  color: metric.accent,
  borderColor: metric.accent,
  background: `${metric.accent}14`
});

const barStyle = (item) => ({
  height: `${Math.max(item.height, item.value > 0 ? 6 : 4)}%`,
  background: item.value > 0 ? selectedMetric.value.accent : '#F2F2F7'
});
</script>

<style lang="scss" scoped>
.chart-container {
  width: 100%;
  background: transparent;
}

.chart-header {
  margin-bottom: 24px;
}

.chart-title {
  display: block;
  font-size: 18px;
  font-weight: 600;
  color: #1d1d1f;
}

.chart-subtitle {
  display: block;
  margin-top: 4px;
  font-size: 13px;
  color: #86868b;
  font-weight: 500;
}

.metric-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
}

.metric-chip {
  padding: 7px 12px;
  border-radius: 999px;
  border: 1px solid transparent;
  background: #f3f5f8;
  color: #6b7280;
  font-size: 12px;
  font-weight: 600;
}

.metric-chip.active {
  box-shadow: 0 6px 14px rgba(15, 23, 42, 0.06);
}

.chart-body {
  position: relative;
  height: 210px;
  width: 100%;
}

.grid-line {
  position: absolute;
  left: 0;
  width: 100%;
  height: 1px;
  background: #e5e5ea;
  z-index: 1;
}

.bars-container {
  position: relative;
  z-index: 2;
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  height: 100%;
  padding-bottom: 24px;
}

.bar-group {
  display: flex;
  flex: 1;
  height: 100%;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
}

.bar-wrapper {
  display: flex;
  width: 100%;
  flex: 1;
  align-items: flex-end;
  justify-content: center;
  padding-bottom: 10px;
}

.bar {
  width: 10px;
  min-height: 4px;
  border-radius: 999px;
  transition: height 0.6s cubic-bezier(0.2, 0.8, 0.2, 1), background 0.3s ease;
}

.bar-value {
  margin-bottom: 4px;
  font-size: 11px;
  font-weight: 600;
  color: #526074;
}

.bar-label {
  font-size: 11px;
  font-weight: 500;
  color: #86868b;
}
</style>
