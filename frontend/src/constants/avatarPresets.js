import coin3d from '../assets/avatars/coin_3d.png';
import bonusImg from '../assets/avatars/Bonus.png';
import giftImg from '../assets/avatars/Gift.png';
import investmentImg from '../assets/avatars/investment.png';
import petsImg from '../assets/avatars/pets.png';
import travelImg from '../assets/avatars/travel.png';
import sportsImg from '../assets/avatars/sports.png';
import educationImg from '../assets/avatars/education.png';
import entertainmentImg from '../assets/avatars/entertainment.png';
import homeImg from '../assets/avatars/Home.png';
import shoppingImg from '../assets/avatars/shopping.png';
import foodImg from '../assets/avatars/food.png';

export const AVATAR_PRESETS = [
  {
    id: 'coin_3d',
    name: 'FinAI Coin 3D',
    tag: 'Linh vật FinAI',
    url: coin3d,
    bgGradient: 'linear-gradient(135deg, #fff3cf 0%, #ffe39a 100%)',
    borderColor: '#f3cd62',
  },
  {
    id: 'investment',
    name: 'Đầu Tư Thịnh Vượng',
    tag: 'Tăng trưởng',
    url: investmentImg,
    bgGradient: 'linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%)',
    borderColor: '#38bdf8',
  },
  {
    id: 'bonus',
    name: 'Túi Vàng May Mắn',
    tag: 'Tài lộc',
    url: bonusImg,
    bgGradient: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)',
    borderColor: '#f59e0b',
  },
  {
    id: 'gift',
    name: 'Hộp Quà Thần Tài',
    tag: 'May mắn',
    url: giftImg,
    bgGradient: 'linear-gradient(135deg, #fce7f3 0%, #fbcfe8 100%)',
    borderColor: '#ec4899',
  },
  {
    id: 'pets',
    name: 'Mèo Thần Tài',
    tag: 'Cute Mascot',
    url: petsImg,
    bgGradient: 'linear-gradient(135deg, #ede9fe 0%, #ddd6fe 100%)',
    borderColor: '#a855f7',
  },
  {
    id: 'travel',
    name: 'Du Lịch Tự Do',
    tag: 'Khám phá',
    url: travelImg,
    bgGradient: 'linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%)',
    borderColor: '#22c55e',
  },
  {
    id: 'education',
    name: 'Cú Thông Thái',
    tag: 'Trí tuệ',
    url: educationImg,
    bgGradient: 'linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 100%)',
    borderColor: '#6366f1',
  },
  {
    id: 'sports',
    name: 'Kỷ Luật Thể Thao',
    tag: 'Bền bỉ',
    url: sportsImg,
    bgGradient: 'linear-gradient(135deg, #ffedd5 0%, #fed7aa 100%)',
    borderColor: '#f97316',
  },
  {
    id: 'home',
    name: 'Mái Ấm Hạnh Phúc',
    tag: 'Gia đình',
    url: homeImg,
    bgGradient: 'linear-gradient(135deg, #fef9c3 0%, #fef08a 100%)',
    borderColor: '#eab308',
  },
  {
    id: 'shopping',
    name: 'Mua Sắm Thông Minh',
    tag: 'Phong cách',
    url: shoppingImg,
    bgGradient: 'linear-gradient(135deg, #fae8ff 0%, #f5d0fe 100%)',
    borderColor: '#d946ef',
  },
  {
    id: 'entertainment',
    name: 'Vui Vẻ Tận Hưởng',
    tag: 'Chill',
    url: entertainmentImg,
    bgGradient: 'linear-gradient(135deg, #ccfbf1 0%, #99f6e4 100%)',
    borderColor: '#14b8a6',
  },
  {
    id: 'food',
    name: 'Ẩm Thực Tinh Hoa',
    tag: 'Đậm đà',
    url: foodImg,
    bgGradient: 'linear-gradient(135deg, #fee2e2 0%, #fecaca 100%)',
    borderColor: '#ef4444',
  },
];