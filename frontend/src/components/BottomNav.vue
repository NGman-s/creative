<template>
  <view class="bottom-nav-placeholder"></view>
  <view class="bottom-nav">
    <view
      class="nav-item"
      :class="{ active: current === 'history' }"
      @tap="navTo('/pages/history/history')"
    >
      <view class="icon-container">
        <svg viewBox="0 0 24 24" class="nav-icon" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M12 8V12L15 15" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="2"/>
        </svg>
      </view>
      <text class="nav-label">历史</text>
    </view>

    <view
      class="nav-item"
      :class="{ active: current === 'home' }"
      @tap="navTo('/pages/index/index')"
    >
      <view class="icon-container">
        <svg viewBox="0 0 24 24" class="nav-icon" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M23 19C23 19.5304 22.7893 20.0391 22.4142 20.4142C22.0391 20.7893 21.5304 21 21 21H3C2.46957 21 1.96086 20.7893 1.58579 20.4142C1.21071 20.0391 1 19.5304 1 19V8C1 7.46957 1.21071 6.96086 1.58579 6.58579C1.96086 6.21071 2.46957 6 3 6H7L9 3H15L17 6H21C21.5304 6 22.0391 6.21071 22.4142 6.58579C22.7893 6.96086 23 7.46957 23 8V19Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          <circle cx="12" cy="13" r="4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </view>
      <text class="nav-label">识别</text>
    </view>

    <view
      class="nav-item"
      :class="{ active: current === 'profile' }"
      @tap="navTo('/pages/profile/profile')"
    >
      <view class="icon-container">
        <svg viewBox="0 0 24 24" class="nav-icon" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M20 21V19C20 17.9391 19.5786 16.9217 18.8284 16.1716C18.0783 15.4214 17.0609 15 16 15H8C6.93913 15 5.92172 15.4214 5.17157 16.1716C4.42143 16.9217 4 17.9391 4 19V21" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          <circle cx="12" cy="7" r="4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </view>
      <text class="nav-label">我的</text>
    </view>
  </view>
</template>

<script setup>
import { defineProps } from 'vue';

const props = defineProps({
  current: {
    type: String,
    default: 'home'
  }
});

const navTo = (url) => {
  // Use redirectTo to avoid building up a large history stack for tab navigation
  // But check if it's the current page first
  const pages = getCurrentPages();
  const currentPage = pages[pages.length - 1];
  if ('/' + currentPage.route === url) return;

  uni.redirectTo({
    url,
    fail: (err) => {
      console.error('Nav failed', err);
    }
  });
};
</script>

<style lang="scss" scoped>
.bottom-nav-placeholder {
  height: calc(50px + env(safe-area-inset-bottom));
  width: 100%;
}

.bottom-nav {
  position: fixed;
  bottom: 0;
  left: 0;
  width: 100%;
  height: calc(50px + env(safe-area-inset-bottom));
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-top: 1px solid rgba(0, 0, 0, 0.1);
  display: flex;
  justify-content: space-around;
  align-items: center;
  padding-bottom: env(safe-area-inset-bottom);
  z-index: 999;
}

.nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  height: 100%;
  color: #86868b; /* Inactive color */
  transition: all 0.2s ease;

  &.active {
    color: #007aff; /* Active color (Apple Blue) */
  }

  &:active {
    opacity: 0.7;
  }
}

.icon-container {
  width: 24px;
  height: 24px;
  margin-bottom: 4px;
}

.nav-icon {
  width: 100%;
  height: 100%;
}

.nav-label {
  font-size: 10px;
  font-weight: 500;
}
</style>
