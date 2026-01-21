<template>
  <view class="page-container">
    <view class="content-wrapper">
      <view class="header">
        <text class="title-large">我的档案</text>
      </view>

      <!-- Personal Info Section -->
      <view class="section-title">基本信息</view>
      <view class="list-group">
        <view class="list-item">
          <text class="item-label">年龄</text>
          <input
            class="item-input"
            type="number"
            v-model="profile.age"
            @blur="saveProfile"
            placeholder="请输入年龄"
          />
        </view>
        <view class="list-divider"></view>
        <view class="list-item">
          <text class="item-label">饮食目标</text>
          <picker
            @change="handleGoalChange"
            :value="goals.findIndex(g => g.value === profile.goal)"
            :range="goals"
            range-key="label"
            class="picker-container"
          >
            <view class="picker-content">
              <text class="picker-value">{{ currentGoalLabel }}</text>
              <text class="chevron">›</text>
            </view>
          </picker>
        </view>
      </view>

      <!-- Health Conditions Section -->
      <view class="section-title">健康偏好</view>
      <view class="list-group">
        <view class="list-item condition-row">
          <text class="item-label">饮食禁忌与状况</text>
        </view>
        <view class="list-divider"></view>
        <view class="conditions-container">
          <view
            v-for="condition in healthConditions"
            :key="condition.value"
            class="chip"
            :class="{ active: profile.health_conditions.includes(condition.value) }"
            @tap="toggleCondition(condition.value)"
          >
            {{ condition.label }}
          </view>
        </view>
      </view>

      <view class="info-footer">
        <text class="info-text">LifeLens AI 将根据您的档案提供个性化建议。</text>
      </view>
    </view>

    <BottomNav current="profile" />
  </view>
</template>

<script setup>
import { computed } from 'vue';
import { useUserStore } from '@/store/user';
import { storeToRefs } from 'pinia';
import BottomNav from '@/components/BottomNav.vue';

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

<style lang="scss" scoped>
.page-container {
  min-height: 100vh;
  padding-bottom: calc(50px + env(safe-area-inset-bottom));
}

.content-wrapper {
  padding: 20px;
}

.header {
  margin-bottom: 24px;
  padding-top: env(safe-area-inset-top);
}

.section-title {
  font-size: 13px;
  color: #86868b;
  margin-bottom: 8px;
  margin-left: 12px;
  text-transform: uppercase;
}

/* iOS Settings Group Style */
.list-group {
  background: #fff;
  border-radius: 12px;
  overflow: hidden;
  margin-bottom: 24px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.02);
}

.list-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: #fff;
  min-height: 54px;
  box-sizing: border-box;
}

.list-divider {
  height: 1px;
  background: #f5f5f7;
  margin-left: 16px;
}

.item-label {
  font-size: 17px;
  color: #1d1d1f;
}

.item-input {
  text-align: right;
  font-size: 17px;
  color: #007aff;
  flex: 1;
  margin-left: 16px;
}

.picker-container {
  flex: 1;
  display: flex;
  justify-content: flex-end;
}

.picker-content {
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

.picker-value {
  font-size: 17px;
  color: #86868b;
  margin-right: 8px;
}

.chevron {
  color: #c7c7cc;
  font-size: 20px;
  font-weight: 400;
  margin-top: -2px;
}

/* Chips for Conditions */
.conditions-container {
  padding: 16px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  background: #fff;
}

.chip {
  padding: 8px 16px;
  background: #f5f5f7;
  border-radius: 100px;
  font-size: 14px;
  color: #1d1d1f;
  transition: all 0.2s ease;

  &.active {
    background: #007aff;
    color: #fff;
    box-shadow: 0 2px 8px rgba(0, 122, 255, 0.2);
  }
}

.info-footer {
  margin-top: 8px;
  padding: 0 12px;
}

.info-text {
  font-size: 13px;
  color: #86868b;
  line-height: 1.4;
}
</style>
