import React from 'react';

// CSS 样式将在 App.css 中定义

function ImagePreviewModal({ imageUrl, onClose }) {
  if (!imageUrl) return null;

  return (
    // 蒙层
    <div className="preview-modal-overlay" onClick={onClose}>
      <div className="preview-modal-content" onClick={(e) => e.stopPropagation()}>
        <button className="preview-modal-close" onClick={onClose}>
          &times;
        </button>
        <img src={imageUrl} alt="Message Source Screenshot" />
      </div>
    </div>
  );
}

export default ImagePreviewModal;