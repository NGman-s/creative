<template>
  <view class="container">
    <!-- HUD Decorative Corners -->
    <view class="hud-corner top-left"></view>
    <view class="hud-corner top-right"></view>
    <view class="hud-corner bottom-left"></view>
    <view class="hud-corner bottom-right"></view>

    <view class="page-header">
      <text class="glitch-text">用户数据加密保护中</text>
    </view>

    <view class="section">
      <text class="section-title">用户档案</text>
      <view class="form-item">
        <text class="label">年龄</text>
        <input class="input" type="number" v-model="profile.age" @input="saveProfile" />
      </view>
      <view class="form-item">
        <text class="label">目标</text>
        <picker @change="handleGoalChange" :value="goals.findIndex(g => g.value === profile.goal)" :range="goals" range-key="label">
          <view class="picker-value">{{ currentGoalLabel }}</view>
        </picker>
      </view>
    </view>

    <view class="section">
      <text class="section-title">健康状况</text>
      <view class="conditions-grid">
        <view
          v-for="condition in healthConditions"
          :key="condition.value"
          class="condition-item"
          :class="{ active: profile.health_conditions.includes(condition.value) }"
          @tap="toggleCondition(condition.value)"
        >
          {{ condition.label }}
        </view>
      </view>
    </view>

    <view class="info-box">
      <text class="info-text">您的档案数据将用于LifeLens AI为您提供个性化的营养建议和红绿灯分级警告。</text>
    </view>
  </view>
</template>

<script setup>
import { computed } from 'vue';
import { useUserStore } from '@/store/user';
import { storeToRefs } from 'pinia';

const userStore = useUserStore();
const { profile } = storeToRefs(userStore);

const goals = [
  { label: '增肌', value: 'muscle_gain' },
  { label: '减脂', value: 'weight_loss' },
  { label: '健康饮食', value: 'healthy_eat' },
  { label: '糖尿病管理', value: 'diabetes' }
];

const healthConditions = [
  { label: '高血压', value: 'Hypertension' },
  { label: '糖尿病', value: 'Diabetes' },
  { label: '高胆固醇', value: 'High Cholesterol' },
  { label: '无麸质', value: 'Gluten Free' },
  { label: '坚果过敏', value: 'Nut Allergy' },
  { label: '乳糖不耐受', value: 'Lactose Intolerant' }
];

const currentGoalLabel = computed(() => {
  const goal = goals.find(g => g.value === profile.value.goal);
  return goal ? goal.label : '选择目标';
});

const handleGoalChange = (e) => {
  const index = e.detail.value;
  profile.value.goal = goals[index].value;
  saveProfile();
};

const toggleCondition = (value) => {
  const index = profile.value.health_conditions.indexOf(value);
  if (index > -1) {
    profile.value.health_conditions.splice(index, 1);
  } else {
    profile.value.health_conditions.push(value);
  }
  saveProfile();
};

const saveProfile = () => {
  userStore.updateProfile(profile.value);
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

.page-header {
  margin-bottom: 20px;
  text-align: right;
  opacity: 0.5;
  font-size: 10px;
}

.glitch-text {
  letter-spacing: 2px;
}

.section {
  margin-bottom: 30px;
  border: 1px solid rgba(0, 243, 255, 0.3);
  padding: 15px;
  background: rgba(0, 0, 0, 0.2);
}

.section-title {
  display: block;
  font-weight: bold;
  letter-spacing: 2px;
  margin-bottom: 20px;
  border-left: 4px solid #00f3ff;
  padding-left: 10px;
}

.form-item {
  margin-bottom: 20px;
}

.label {
  display: block;
  font-size: 12px;
  margin-bottom: 5px;
  opacity: 0.8;
}

.input {
  background: rgba(0, 243, 255, 0.1);
  border: 1px solid #00f3ff;
  color: #00f3ff;
  padding: 10px;
  font-size: 16px;
  width: 100%;
  box-sizing: border-box;
}

.picker-value {
  background: rgba(0, 243, 255, 0.1);
  border: 1px solid #00f3ff;
  padding: 10px;
  font-size: 16px;
}

.conditions-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.condition-item {
  padding: 8px 12px;
  border: 1px solid rgba(0, 243, 255, 0.5);
  font-size: 12px;
  transition: all 0.3s;
}

.condition-item.active {
  background: #00f3ff;
  color: #00141e;
  box-shadow: 0 0 10px #00f3ff;
}

.info-box {
  background: rgba(0, 243, 255, 0.05);
  padding: 15px;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.5;
  border: 1px dashed rgba(0, 243, 255, 0.3);
}
</style>
