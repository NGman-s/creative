<template>
  <view class="container">
    <!-- Camera View Finder / Background Image -->
    <view class="viewfinder" @tap="handleCapture">
      <image v-if="capturedImage" :src="capturedImage" mode="aspectFill" class="bg-image"></image>
      <view v-else class="camera-placeholder">
        <text class="placeholder-icon">📸</text>
        <text class="placeholder-text">点击扫描食物</text>
      </view>
    </view>

    <!-- Header / Logo -->
    <view class="header">
      <image
        class="logo"
        src="/static/logo.png"
        @tap="handleLogoClick"
      ></image>
      <text class="app-name">LIFELENS</text>
    </view>

    <!-- HUD Overlay -->
    <ResultOverlay
      :visible="showOverlay"
      :loading="loading"
      :result="analysisResult"
      @close="closeOverlay"
    />

    <!-- Bottom Controls -->
    <view class="controls" v-if="!showOverlay">
      <view class="btn side-btn" @tap="navigateTo('/pages/history/history')">
        <text class="icon">📜</text>
      </view>
      <view class="btn capture-btn" @tap="handleCapture">
        <view class="btn-inner"></view>
      </view>
      <view class="btn gallery-btn" @tap="handleGallery">
        <text class="icon">🖼️</text>
      </view>
      <view class="btn side-btn" @tap="navigateTo('/pages/profile/profile')">
        <text class="icon">👤</text>
      </view>
    </view>

    <view class="mock-badge" v-if="mockMode">模拟模式已激活</view>
  </view>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useUserStore } from '@/store/user';
import { chooseImage, compressImage } from '@/utils/image';
import { checkCameraPermission, checkGalleryPermission } from '@/utils/permission';
import Api from '@/utils/request';
import ResultOverlay from '@/components/ResultOverlay.vue';

const userStore = useUserStore();

const capturedImage = ref(null);
const showOverlay = ref(false);
const loading = ref(false);
const analysisResult = ref(null);
const mockMode = ref(false);
const clickCount = ref(0);

// Dynamic Mock Data for Demo
const getMockResult = (goal) => {
  const baseResult = {
    thought_process: "正在识别食物... 检测到烤鸡胸肉和新鲜混合蔬菜。正在对照用户健康档案和历史数据。",
    items: [
      {
        name: "烤鸡胸肉沙拉",
        calories: 350,
        unit: "千卡",
        nutrition_tags: ["高蛋白", "低碳水"],
        traffic_light: "green"
      }
    ],
    total_analysis: {
      summary: "富含优质蛋白和纤维的均衡膳食。",
      suggestion: "非常适合您当前的健康状况。",
      confidence: 0.99
    }
  };

  // Adjust mock based on goal for demonstration impact
  if (goal === 'diabetes') {
    baseResult.thought_process += " 警告：用户有糖尿病史。正在扫描高升糖成分... 未检测到淀粉。";
    baseResult.total_analysis.suggestion = "血糖管理安全。避免使用蜂蜜芥末酱。";
  } else if (goal === 'weight_loss') {
    baseResult.thought_process += " 优化：正在计算纤维热量比。检测到高密度。";
    baseResult.total_analysis.suggestion = "非常适合热量亏缺。饱腹感指数：高。";
  }

  return baseResult;
};

const handleLogoClick = () => {
  clickCount.value++;
  if (clickCount.value >= 5) {
    mockMode.value = !mockMode.value;
    uni.showToast({
      title: mockMode.value ? '模拟模式开启' : '模拟模式关闭',
      icon: 'none'
    });
    clickCount.value = 0;
  }
};

const navigateTo = (url) => {
  uni.navigateTo({ url });
};

const handleCapture = async () => {
  try {
    await checkCameraPermission();
    const path = await chooseImage(['camera']);
    processImage(path);
  } catch (e) {
    console.error('Capture failed', e);
    uni.showModal({
      title: '需要权限',
      content: '扫描食物需要相机权限，请在设置中开启。',
      showCancel: false
    });
  }
};

const handleGallery = async () => {
  try {
    await checkGalleryPermission();
    const path = await chooseImage(['album']);
    processImage(path);
  } catch (e) {
    console.error('Gallery selection failed', e);
    uni.showModal({
      title: '需要权限',
      content: '选择食物图片需要存储权限，请在设置中开启。',
      showCancel: false
    });
  }
};

const processImage = async (path) => {
  capturedImage.value = path;
  showOverlay.value = true;
  loading.value = true;

  try {
    const compressedPath = await compressImage(path);

    if (mockMode.value) {
      // Artificial delay for mock mode
      setTimeout(() => {
        finishAnalysis(getMockResult(userStore.profile.goal));
      }, 1500);
      return;
    }

    // Set a 60s timeout
    const timeoutId = setTimeout(() => {
      if (loading.value) {
        console.warn('API Timeout');
        loading.value = false;
        uni.showToast({
          title: '请求超时，请重试',
          icon: 'none'
        });
      }
    }, 60000);

    const res = await Api.uploadFile({
      url: '/api/v1/vision/analyze',
      filePath: compressedPath,
      timeout: 60000,
      formData: {
        user_context: JSON.stringify(userStore.profile)
      }
    });

    clearTimeout(timeoutId);

    if (res.code === 200) {
      finishAnalysis(res.data);
    } else {
      throw new Error(res.message || '分析失败');
    }
  } catch (e) {
    console.error('Analysis error', e);
    loading.value = false;
    uni.showToast({
      title: e.message || '识别失败，请检查网络或重试',
      icon: 'none',
      duration: 3000
    });
  }
};

const finishAnalysis = (result) => {
  analysisResult.value = result;
  loading.value = false;
  // Save to history
  userStore.addHistoryEntry({
    image: capturedImage.value,
    result: result
  });
};

const closeOverlay = () => {
  showOverlay.value = false;
  analysisResult.value = null;
  loading.value = false;
};

// Start camera on mount if needed (simulated by immediate prompt or UI design)
onMounted(() => {
  console.log('LifeLens Initialized');
});
</script>

<style scoped>
.container {
  position: relative;
  width: 100vw;
  height: 100vh;
  background-color: #000;
  overflow: hidden;
}

.viewfinder {
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
}

.bg-image {
  width: 100%;
  height: 100%;
}

.camera-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  color: #00f3ff;
}

.placeholder-icon {
  font-size: 80px;
  margin-bottom: 20px;
  text-shadow: 0 0 20px #00f3ff;
}

.placeholder-text {
  font-family: 'Courier New', Courier, monospace;
  letter-spacing: 4px;
  font-weight: bold;
}

.header {
  position: absolute;
  top: calc(40px + env(safe-area-inset-top));
  left: 20px;
  display: flex;
  align-items: center;
  z-index: 10;
}

.logo {
  width: 40px;
  height: 40px;
  margin-right: 10px;
  border: 1px solid #00f3ff;
  border-radius: 50%;
  padding: 2px;
}

.app-name {
  color: #00f3ff;
  font-size: 20px;
  font-weight: bold;
  letter-spacing: 2px;
  text-shadow: 0 0 10px #00f3ff;
}

.controls {
  position: absolute;
  bottom: calc(50px + env(safe-area-inset-bottom));
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 40px;
}

.btn {
  display: flex;
  justify-content: center;
  align-items: center;
  background: rgba(0, 0, 0, 0.5);
  border: 2px solid #00f3ff;
  border-radius: 50%;
  box-shadow: 0 0 15px rgba(0, 243, 255, 0.5);
}

.capture-btn {
  width: 80px;
  height: 80px;
}

.btn-inner {
  width: 60px;
  height: 60px;
  background: #00f3ff;
  border-radius: 50%;
}

.gallery-btn, .side-btn {
  width: 50px;
  height: 50px;
}

.mock-badge {
  position: absolute;
  top: 100px;
  left: 20px;
  background: red;
  color: white;
  font-size: 10px;
  padding: 2px 5px;
  font-weight: bold;
  z-index: 10;
}
</style>
