import { memo, useEffect, useState } from 'react';
import { compactIconAssetPath, iconFallback, iconScale } from '../constants/categoryIcons';

const CategoryIcon = ({ icon, color, className = '', loading = 'eager', compact = false }) => {
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    setFailed(false);
  }, [icon]);

  return (
    <span
      className={`category-icon ${className}`}
      style={{ '--category-color': color, '--icon-scale': iconScale(icon) }}
      aria-hidden="true"
    >
      {!failed && (
        <img
          src={compactIconAssetPath(icon, compact)}
          alt=""
          decoding="async"
          loading={loading}
          draggable="false"
          onError={() => setFailed(true)}
        />
      )}
      {failed && <span className="category-icon-fallback">{iconFallback(icon)}</span>}
    </span>
  );
};

export default memo(CategoryIcon);
