import bonusAsset from '../assets/Bonus.png';
import educationAsset from '../assets/education.png';
import entertainmentAsset from '../assets/entertainment.png';
import foodAsset from '../assets/food.png';
import giftAsset from '../assets/Gift.png';
import healthAsset from '../assets/health.png';
import homeAsset from '../assets/Home.png';
import investmentAsset from '../assets/investment.png';
import otherAsset from '../assets/other.png';
import shoppingAsset from '../assets/shopping.png';
import salaryAsset from '../assets/slary.png';
import transportAsset from '../assets/transport.png';
import sportsAsset from '../assets/sports.png';
import petsAsset from '../assets/pets.png';
import travelAsset from '../assets/travel.png';

export const CATEGORY_PRESETS = [
  { value: 'food', label: 'Ăn uống', type: 'expense', fallback: '🍜', asset: foodAsset, scale: 1.05, color: '#E76452' },
  { value: 'transport', label: 'Đi lại', type: 'expense', fallback: '🛵', asset: transportAsset, scale: 1.48, color: '#4F8CC9' },
  { value: 'shopping', label: 'Mua sắm', type: 'expense', fallback: '🛍️', asset: shoppingAsset, scale: 0.88, color: '#9A6AC4' },
  { value: 'home', label: 'Nhà ở', type: 'expense', fallback: '🏠', asset: homeAsset, scale: 1.8, color: '#D87542' },
  { value: 'health', label: 'Sức khỏe', type: 'expense', fallback: '🩺', asset: healthAsset, scale: 0.92, color: '#DE5555' },
  { value: 'education', label: 'Giáo dục', type: 'expense', fallback: '📚', asset: educationAsset, scale: 0.92, color: '#4F72BE' },
  { value: 'entertainment', label: 'Giải trí', type: 'expense', fallback: '🎬', asset: entertainmentAsset, scale: 1.1, color: '#7D5BB2' },
  { value: 'salary', label: 'Lương', type: 'income', fallback: '💼', asset: salaryAsset, scale: 2, color: '#4B9D67' },
  { value: 'bonus', label: 'Thưởng', type: 'income', fallback: '🏆', asset: bonusAsset, scale: 1.55, color: '#E9A22F' },
  { value: 'gift', label: 'Quà tặng', type: 'income', fallback: '🎁', asset: giftAsset, scale: 2.25, color: '#DD5C77' },
  { value: 'investment', label: 'Đầu tư', type: 'income', fallback: '📈', asset: investmentAsset, scale: 0.9, color: '#719F4E' },
  { value: 'sports', label: 'Thể thao', type: 'expense', fallback: '🏋️', asset: sportsAsset, scale: 1.2, color: '#F59E0B' },
  { value: 'pets', label: 'Thú cưng', type: 'expense', fallback: '🐾', asset: petsAsset, scale: 1.2, color: '#EC4899' },
  { value: 'travel', label: 'Du lịch', type: 'expense', fallback: '✈️', asset: travelAsset, scale: 1.2, color: '#3B82F6' },
  { value: 'other', label: 'Khác', type: 'expense', fallback: '✨', asset: otherAsset, scale: 1.65, color: '#D69A23' },
];

export const CATEGORY_ICONS = CATEGORY_PRESETS;

export const CATEGORY_COLORS = [
  '#D69A23', '#E76452', '#DE5555', '#DD5C77', '#9A6AC4',
  '#4F72BE', '#4F8CC9', '#2F9B92', '#4B9D67', '#719F4E',
];

export const categoryIcon = (icon) => (
  CATEGORY_PRESETS.find((item) => item.value === icon)
  || CATEGORY_PRESETS.find((item) => item.value === 'other')
);

export const iconAssetPath = (icon) => categoryIcon(icon).asset;
export const iconFallback = (icon) => categoryIcon(icon).fallback;
export const iconScale = (icon) => categoryIcon(icon).scale;

let iconPreloadPromise;

export const preloadCategoryIconAssets = () => {
  if (iconPreloadPromise || typeof Image === 'undefined') return iconPreloadPromise;
  iconPreloadPromise = (async () => {
    for (const preset of CATEGORY_PRESETS) {
      const image = new Image();
      image.decoding = 'async';
      image.src = preset.asset;
      if (typeof image.decode === 'function') {
        try {
          await image.decode();
        } catch {
          // CategoryIcon still provides a visible fallback if an asset fails.
        }
      }
    }
  })();
  return iconPreloadPromise;
};
