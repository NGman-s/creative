<template>
  <view class="container">
    <!-- HUD Decorative Corners -->
    <view class="hud-corner top-left"></view>
    <view class="hud-corner top-right"></view>
    <view class="hud-corner bottom-left"></view>
    <view class="hud-corner bottom-right"></view>

    <view class="header">
      <text class="title">饮食记录归档</text>
      <text class="clear-btn" @tap="handleClear">清空数据</text>
    </view>

    <!-- Trend Chart -->
    <TrendChart :data="weeklyStats" />

    <scroll-view scroll-y class="history-list">
      <view v-if="history.length === 0" class="empty-state">
        <text class="empty-icon">🗄️</text>
        <text class="empty-text">暂无记录</text>
      </view>

      <view v-for="entry in history" :key="entry.id" class="history-item">
        <image :src="entry.image" mode="aspectFill" class="item-image"></image>
        <view class="item-info">
          <view class="item-header">
            <text class="item-name">{{ entry.result.items[0]?.name || '未知菜品' }}</text>
            <view class="traffic-light" :class="entry.result.items[0]?.traffic_light"></view>
          </view>
          <text class="item-time">{{ formatDate(entry.timestamp) }}</text>
          <text class="item-summary">{{ entry.result.total_analysis.summary }}</text>
        </view>
      </view>
    </scroll-view>
  </view>
</template>

<script setup>
import { useUserStore } from '@/store/user';
import { storeToRefs } from 'pinia';
import TrendChart from '@/components/TrendChart.vue';

const userStore = useUserStore();
const { history, weeklyStats } = storeToRefs(userStore);

const formatDate = (isoString) => {
  const date = new Date(isoString);
  return date.toLocaleString('zh-CN');
};

const handleClear = () => {
  uni.showModal({
    title: '确认',
    content: '是否清空所有历史记录？',
    confirmText: '确认',
    cancelText: '取消',
    success: (res) => {
      if (res.confirm) {
        userStore.clearHistory();
      }
    }
  });
};
</script>

<style scoped>
.container {
  min-height: 100vh;
  background-color: #00141e;
  padding: calc(20px + env(safe-area-inset-top)) 20px calc(20px + env(safe-area-inset-bottom));
  color: #00f3ff;
  font-family: 'Courier New', Courier, monospace;
  position: relative;
}

.hud-corner {
  position: fixed;
  width: 20px;
  height: 20px;
  border: 2px solid #00f3ff;
  z-index: 100;
  pointer-events: none;
  filter: drop-shadow(0 0 5px #00f3ff);
}

.top-left { top: calc(10px + env(safe-area-inset-top)); left: 10px; border-right: none; border-bottom: none; }
.top-right { top: calc(10px + env(safe-area-inset-top)); right: 10px; border-left: none; border-bottom: none; }
.bottom-left { bottom: calc(10px + env(safe-area-inset-bottom)); left: 10px; border-right: none; border-top: none; }
.bottom-right { bottom: calc(10px + env(safe-area-inset-bottom)); right: 10px; border-left: none; border-top: none; }

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  border-bottom: 1px solid rgba(0, 243, 255, 0.3);
  padding-bottom: 10px;
}

.title {
  font-weight: bold;
  letter-spacing: 2px;
}

.clear-btn {
  font-size: 12px;
  border: 1px solid #ff0000;
  color: #ff0000;
  padding: 2px 8px;
}

.history-list {
  height: calc(100vh - 100px);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-top: 100px;
  opacity: 0.5;
}

.empty-icon {
  font-size: 50px;
  margin-bottom: 10px;
}

.history-item {
  display: flex;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(0, 243, 255, 0.2);
  margin-bottom: 15px;
  padding: 10px;
}

.item-image {
  width: 80px;
  height: 80px;
  margin-right: 15px;
  border: 1px solid rgba(0, 243, 255, 0.5);
}

.item-info {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.item-name {
  font-weight: bold;
  font-size: 16px;
  text-transform: uppercase;
}

.traffic-light {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.traffic-light.green { background: #00ff00; box-shadow: 0 0 5px #00ff00; }
.traffic-light.yellow { background: #ffff00; box-shadow: 0 0 5px #ffff00; }
.traffic-light.red { background: #ff0000; box-shadow: 0 0 5px #ff0000; }

.item-time {
  font-size: 10px;
  opacity: 0.6;
  margin-bottom: 5px;
}

.item-summary {
  font-size: 12px;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
}
</style>
