import React from 'react';

// [移除] const styles = { ... } (所有样式都移到 APP.css 了)

function EditableMessage({ message, profile, onChange }) {

  const nameMap = {
    'User 1': profile.user_name || 'User 1 (我)',
    'User 2': profile.opponent_name || 'User 2 (对方)',
    'system': 'System',
  };

  const handleTimestampChange = (e) => {
    try {
        // 允许输入为空
        if (!e.target.value) {
            onChange('timestamp', null);
            return;
        }
        const isoString = new Date(e.target.value).toISOString();
        onChange('timestamp', isoString);
    } catch(e) {
        // 忽略无效日期
    }
  };

  const formatISODateForInput = (isoString) => {
    try {
        if (!isoString) return '';
        const date = new Date(isoString);
        // 检查日期是否有效
        if (isNaN(date.getTime())) return '';
        // 修复时区问题：转换为本地时间再截取
        const offset = date.getTimezoneOffset();
        const localDate = new Date(date.getTime() - (offset * 60000));
        return localDate.toISOString().slice(0, 16);
    } catch (e) {
        return '';
    }
  };

  // [修改] 动态 className
  const containerClasses = [
    'editable-message',
    `type-${message.content_type}`,
    message.is_editable ? 'is-editable' : ''
  ].join(' ');

  return (
    <div className={containerClasses}>
      <select
        value={message.sender}
        onChange={(e) => onChange('sender', e.target.value)}
      >
        <option value="User 1">{nameMap['User 1']}</option>
        <option value="User 2">{nameMap['User 2']}</option>
        <option value="system">{nameMap['system']}</option>
      </select>

      <input
        type="datetime-local"
        value={formatISODateForInput(message.timestamp)}
        onChange={handleTimestampChange}
        step="1" // 允许选择到秒 (如果需要)
      />

      {/* [修改] 使用 className 和条件渲染 */}
      <input
        type="text"
        className="text-input"
        placeholder="文本内容"
        value={message.text || ''}
        onChange={(e) => onChange('text', e.target.value)}
      />

       <input
        type="text"
        className="media-input"
        placeholder="媒体/系统描述 (e.g., [图片])"
        value={message.media_description || ''}
        onChange={(e) => onChange('media_description', e.target.value)}
      />
    </div>
  );
}

export default EditableMessage;