export const DEFAULT_NUTRITION_TOTALS = Object.freeze({
  calories_kcal: 0,
  protein_g: 0,
  fat_g: 0,
  carb_g: 0,
  fiber_g: 0,
  sugar_g: 0,
  sodium_mg: 0
});

const NUTRITION_PRECISION = {
  calories_kcal: 0,
  protein_g: 1,
  fat_g: 1,
  carb_g: 1,
  fiber_g: 1,
  sugar_g: 1,
  sodium_mg: 0
};

export const NUTRITION_OVERVIEW_METRICS = [
  { key: 'protein_g', label: '蛋白质', unit: 'g', accent: 'protein' },
  { key: 'fat_g', label: '脂肪', unit: 'g', accent: 'fat' },
  { key: 'carb_g', label: '碳水', unit: 'g', accent: 'carb' },
  { key: 'fiber_g', label: '纤维', unit: 'g', accent: 'fiber' },
  { key: 'sugar_g', label: '糖', unit: 'g', accent: 'sugar' },
  { key: 'sodium_mg', label: '钠', unit: 'mg', accent: 'sodium' }
];

export const TREND_METRICS = [
  { key: 'calories', totalsKey: 'calories_kcal', label: '热量', unit: 'kcal', maxFloor: 2500, accent: '#007AFF' },
  { key: 'protein', totalsKey: 'protein_g', label: '蛋白质', unit: 'g', maxFloor: 140, accent: '#34C759' },
  { key: 'fat', totalsKey: 'fat_g', label: '脂肪', unit: 'g', maxFloor: 120, accent: '#FF9500' },
  { key: 'carb', totalsKey: 'carb_g', label: '碳水', unit: 'g', maxFloor: 320, accent: '#5856D6' }
];

const toNumber = (value) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
};

const normalizeValue = (key, value) => {
  const precision = NUTRITION_PRECISION[key] || 0;
  const normalized = Math.max(0, toNumber(value));
  if (precision === 0) {
    return Math.round(normalized);
  }
  return Number(normalized.toFixed(precision));
};

export const normalizeNutritionTotals = (totals = {}, fallbackCalories = 0) => {
  const source = totals && typeof totals === 'object' ? totals : {};
  const normalized = {
    calories_kcal: normalizeValue('calories_kcal', source.calories_kcal ?? fallbackCalories),
    protein_g: normalizeValue('protein_g', source.protein_g),
    fat_g: normalizeValue('fat_g', source.fat_g),
    carb_g: normalizeValue('carb_g', source.carb_g),
    fiber_g: normalizeValue('fiber_g', source.fiber_g),
    sugar_g: normalizeValue('sugar_g', source.sugar_g),
    sodium_mg: normalizeValue('sodium_mg', source.sodium_mg)
  };

  if (!normalized.calories_kcal && fallbackCalories) {
    normalized.calories_kcal = normalizeValue('calories_kcal', fallbackCalories);
  }

  return normalized;
};

export const hasNutritionData = (totals = {}) =>
  Object.keys(DEFAULT_NUTRITION_TOTALS).some((key) => toNumber(totals[key]) > 0);

export const getNutritionTotalsFromResult = (result = {}) => {
  const topTotals = normalizeNutritionTotals(
    result?.nutrition_totals,
    result?.total_calories || result?.items?.[0]?.calories || 0
  );

  if (hasNutritionData(topTotals)) {
    return topTotals;
  }

  const summed = { ...DEFAULT_NUTRITION_TOTALS };
  (result?.items || []).forEach((item) => {
    const itemTotals = normalizeNutritionTotals(item?.nutrition, item?.calories || 0);
    Object.keys(summed).forEach((key) => {
      summed[key] += toNumber(itemTotals[key]);
    });
  });

  return normalizeNutritionTotals(summed, result?.total_calories || 0);
};

export const getNutritionTagsFromResult = (result = {}) => {
  if (Array.isArray(result?.nutrition_tags) && result.nutrition_tags.length) {
    return result.nutrition_tags;
  }
  if (Array.isArray(result?.items?.[0]?.nutrition_tags) && result.items[0].nutrition_tags.length) {
    return result.items[0].nutrition_tags;
  }
  return [];
};

export const getRiskFlagsFromResult = (result = {}) =>
  Array.isArray(result?.risk_flags) ? result.risk_flags : [];

export const formatNutritionValue = (key, value) => {
  const normalized = normalizeValue(key, value);
  const precision = NUTRITION_PRECISION[key] || 0;
  if (precision === 0) {
    return `${normalized}`;
  }
  return Number.isInteger(normalized) ? `${normalized}` : normalized.toFixed(precision);
};

export const buildMacroSummary = (totals = {}) => {
  const normalized = normalizeNutritionTotals(totals);
  return [
    `蛋白 ${formatNutritionValue('protein_g', normalized.protein_g)}g`,
    `脂肪 ${formatNutritionValue('fat_g', normalized.fat_g)}g`,
    `碳水 ${formatNutritionValue('carb_g', normalized.carb_g)}g`
  ].join(' · ');
};

