<template>
  <view class="hud-container" v-if="visible">
    <!-- Scanning Line Effect -->
    <view class="scanner-line" v-if="loading"></view>

    <!-- HUD Overlay Content -->
    <view class="hud-content" v-if="!loading && result">
      <!-- HUD Border Decor -->
      <view class="hud-corner top-left"></view>
      <view class="hud-corner top-right"></view>
      <view class="hud-corner bottom-left"></view>
      <view class="hud-corner bottom-right"></view>

      <!-- Decorative HUD Elements -->
      <view class="hud-decor-line"></view>
      <view class="hud-status-bar">
        <text class="status-item">纬度: 39.9042</text>
        <text class="status-item">经度: 116.4074</text>
        <text class="status-item">系统: 在线</text>
      </view>

      <view class="result-header">
        <text class="title">AI 视觉分析 v3.0</text>
        <view class="traffic-light" :class="result.items[0]?.traffic_light"></view>
      </view>

      <!-- Thought Process (New) -->
      <view class="thought-process" v-if="result.thought_process">
        <text class="thought-label">分析逻辑 > </text>
        <text class="thought-text">{{ result.thought_process }}</text>
      </view>

      <view class="dish-info" v-for="(item, index) in result.items" :key="index">
        <view class="dish-name">{{ item.name }}</view>
        <view class="nutrition-grid">
          <view class="grid-item">
            <text class="label">热量</text>
            <text class="value">{{ item.calories }} {{ item.unit }}</text>
          </view>
          <view class="grid-item">
            <text class="label">标签</text>
            <view class="tags">
              <text v-for="tag in item.nutrition_tags" :key="tag" class="tag-chip">{{ tag }}</text>
            </view>
          </view>
        </view>
      </view>

      <view class="analysis-summary">
        <view class="summary-label">总结</view>
        <view class="summary-text">{{ result.total_analysis.summary }}</view>
        <view class="suggestion-label">建议</view>
        <view class="suggestion-text">{{ result.total_analysis.suggestion }}</view>
      </view>

      <view class="close-btn" @tap="$emit('close')">关闭</view>
    </view>

    <view class="loading-status" v-if="loading">
      <text class="loading-text">正在扫描中...</text>
      <view class="progress-bar-container">
        <view class="progress-bar-fill"></view>
      </view>

      <!-- Dynamic Scanning Logs -->
      <view class="log-container">
        <view v-for="(log, index) in currentLogs" :key="index" class="log-item">
          <text class="log-prefix">></text> {{ log }}
        </view>
      </view>

      <text class="loading-sub">正在分析分子结构</text>
    </view>
  </view>
</template>

<script setup>
import { ref, watch, onUnmounted, defineProps, defineEmits } from 'vue';

const props = defineProps({
  visible: Boolean,
  loading: Boolean,
  result: Object
});

const emit = defineEmits(['close']);

const allLogs = [
  '正在初始化光学传感器...',
  '正在捕获图像数据...',
  '正在提取像素特征...',
  '正在映射几何向量...',
  '正在查询营养数据库...',
  '正在运行多模态推理...',
  '正在估算热量密度...',
  '正在交叉对比用户档案...',
  '正在生成健康报告...'
];

const currentLogs = ref([]);
let logInterval = null;

watch(() => props.loading, (newVal) => {
  if (newVal) {
    currentLogs.value = [allLogs[0]];
    let index = 1;
    logInterval = setInterval(() => {
      if (index < allLogs.length) {
        currentLogs.value.push(allLogs[index]);
        if (currentLogs.value.length > 4) {
          currentLogs.value.shift();
        }
        index++;
      } else {
        clearInterval(logInterval);
      }
    }, 600);
  } else {
    clearInterval(logInterval);
    currentLogs.value = [];
  }
});

onUnmounted(() => {
  clearInterval(logInterval);
});
</script>

<style scoped>
.hud-container {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 100;
  pointer-events: auto;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  background-color: rgba(0, 0, 0, 0.2);
}

/* Scanner Line */
.scanner-line {
  position: absolute;
  width: 100%;
  height: 4px;
  background: linear-gradient(to bottom, transparent, #00f3ff, transparent);
  box-shadow: 0 0 15px #00f3ff;
  top: 0;
  animation: scan 2s linear infinite;
  z-index: 101;
}

@keyframes scan {
  0% { top: 0; }
  100% { top: 100%; }
}

/* HUD Content */
.hud-content {
  position: relative;
  width: 85%;
  background: rgba(0, 20, 30, 0.85);
  border: 1px solid #00f3ff;
  padding: 20px;
  color: #00f3ff;
  font-family: 'Courier New', Courier, monospace;
  box-shadow: 0 0 20px rgba(0, 243, 255, 0.3);
  backdrop-filter: blur(5px);
}

/* Flicker Animation for HUD Text */
.title, .dish-name, .loading-text {
  animation: flicker 3s infinite;
}

@keyframes flicker {
  0% { opacity: 1; }
  3% { opacity: 0.8; }
  6% { opacity: 1; }
  7% { opacity: 0.9; }
  8% { opacity: 1; }
  9% { opacity: 0.6; }
  10% { opacity: 1; }
  89% { opacity: 1; }
  90% { opacity: 0.8; }
  100% { opacity: 1; }
}

.hud-corner {
  position: absolute;
  width: 20px;
  height: 20px;
  border: 2px solid #00f3ff;
  filter: drop-shadow(0 0 5px #00f3ff);
}

.top-left { top: -2px; left: -2px; border-right: none; border-bottom: none; }
.top-right { top: -2px; right: -2px; border-left: none; border-bottom: none; }
.bottom-left { bottom: -2px; left: -2px; border-right: none; border-top: none; }
.bottom-right { bottom: -2px; right: -2px; border-left: none; border-top: none; }

.hud-decor-line {
  position: absolute;
  top: 10px;
  right: 50px;
  width: 100px;
  height: 1px;
  background: linear-gradient(to right, transparent, #00f3ff);
}

.hud-status-bar {
  display: flex;
  gap: 15px;
  font-size: 8px;
  margin-bottom: 10px;
  opacity: 0.6;
}

.status-item {
  position: relative;
}

.thought-process {
  font-size: 10px;
  background: rgba(0, 243, 255, 0.05);
  padding: 8px;
  margin-bottom: 15px;
  border: 1px dashed rgba(0, 243, 255, 0.2);
  line-height: 1.2;
}

.thought-label {
  font-weight: bold;
  color: #fff;
}

.thought-text {
  font-style: italic;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  border-bottom: 1px solid rgba(0, 243, 255, 0.5);
  padding-bottom: 5px;
}

.title {
  font-weight: bold;
  letter-spacing: 2px;
  font-size: 14px;
}

.traffic-light {
  width: 15px;
  height: 15px;
  border-radius: 50%;
  box-shadow: 0 0 10px currentColor;
}

.traffic-light.green { color: #00ff00; background-color: #00ff00; }
.traffic-light.yellow { color: #ffff00; background-color: #ffff00; }
.traffic-light.red { color: #ff0000; background-color: #ff0000; }

.dish-name {
  font-size: 20px;
  font-weight: bold;
  margin-bottom: 10px;
  text-transform: uppercase;
}

.nutrition-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 15px;
  margin-bottom: 15px;
}

.label {
  font-size: 10px;
  display: block;
  opacity: 0.8;
}

.value {
  font-size: 16px;
  font-weight: bold;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.tag-chip {
  font-size: 10px;
  background: rgba(0, 243, 255, 0.2);
  border: 1px solid #00f3ff;
  padding: 2px 5px;
}

.analysis-summary {
  font-size: 12px;
  background: rgba(0, 0, 0, 0.3);
  padding: 10px;
  border-left: 2px solid #00f3ff;
}

.summary-label, .suggestion-label {
  font-weight: bold;
  font-size: 10px;
  margin-bottom: 2px;
  color: #fff;
}

.summary-text, .suggestion-text {
  margin-bottom: 8px;
  line-height: 1.4;
}

.close-btn {
  margin-top: 15px;
  text-align: center;
  padding: 10px;
  border: 1px solid #00f3ff;
  font-size: 14px;
  font-weight: bold;
  transition: all 0.3s;
}

.close-btn:active {
  background: #00f3ff;
  color: #00141e;
}

.loading-status {
  background: rgba(0, 20, 30, 0.7);
  padding: 20px;
  text-align: center;
  border: 1px solid #00f3ff;
  color: #00f3ff;
}

.loading-text {
  display: block;
  font-weight: bold;
  margin-bottom: 5px;
}

.loading-sub {
  font-size: 10px;
  opacity: 0.8;
}

.progress-bar-container {
  width: 100%;
  height: 2px;
  background: rgba(0, 243, 255, 0.2);
  margin: 15px 0;
  position: relative;
  overflow: hidden;
}

.progress-bar-fill {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background: #00f3ff;
  box-shadow: 0 0 10px #00f3ff;
  animation: progress 2s infinite ease-in-out;
}

.log-container {
  height: 80px;
  width: 100%;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  align-items: flex-start;
  overflow: hidden;
  margin-bottom: 10px;
}

.log-item {
  font-size: 8px;
  color: #00f3ff;
  opacity: 0.7;
  margin-bottom: 4px;
  font-family: 'Courier New', Courier, monospace;
}

.log-prefix {
  font-weight: bold;
  margin-right: 5px;
}

@keyframes progress {
  0% { width: 0%; left: 0%; }
  50% { width: 100%; left: 0%; }
  100% { width: 0%; left: 100%; }
}
</style>