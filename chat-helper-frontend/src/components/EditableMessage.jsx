import React from 'react';

// [新增] 定义内容类型选项，包含您要求的中文标签
const contentTypeOptions = [
  { value: 'text', label: '文本' },
  { value: 'image', label: '图片' },
  { value: 'video', label: '视频' },
  { value: 'transfer', label: '转账' },
  { value: 'emoji', label: '表情' },
  { value: 'system', label: '系统' },
  { value: 'unknown', label: '未知' },
];

function EditableMessage({
  message,
  profile,
  onChange,
  onMove,
  onDelete,
  isFirstInGroup,
  isLastInGroup
}) {

  const nameMap = {
    'User 1': profile.user_name || 'User 1 (我)',
    'User 2': profile.opponent_name || 'User 2 (对方)',
    'system': 'System',
  };

  const handleTimestampChange = (e) => {
    try {
        if (!e.target.value) {
            onChange('timestamp', null);
            return;
        }
        const isoString = new Date(e.target.value).toISOString();
        onChange('timestamp', isoString);
    } catch(_e) {
        // 忽略无效日期
    }
  };

  const formatISODateForInput = (isoString) => {
    try {
        if (!isoString) return '';
        const date = new Date(isoString);
        if (isNaN(date.getTime())) return '';
        const offset = date.getTimezoneOffset();
        const localDate = new Date(date.getTime() - (offset * 60000));
        return localDate.toISOString().slice(0, 16);
    } catch (_e) {
        return '';
    }
  };

  const containerClasses = [
    'editable-message',
    message.is_editable ? 'error' : '',
    `type-${message.content_type}`
  ].join(' ');

  return (
    <div className={containerClasses}>
      {/* 1. 发送者 */}
      <select
        value={message.sender}
        onChange={(e) => onChange('sender', e.target.value)}
      >
        <option value="User 1">{nameMap['User 1']}</option>
        <option value="User 2">{nameMap['User 2']}</option>
        <option value="system">{nameMap['system']}</option>
      </select>

      {/* 2. [新增] 内容类型 */}
      <select
        className="message-type-select"
        value={message.content_type}
        onChange={(e) => onChange('content_type', e.target.value)}
      >
        {contentTypeOptions.map(opt => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>

      {/* 3. 时间戳 */}
      <input
        type="datetime-local"
        className={
          (message.auto_filled_date || message.auto_filled_time)
          ? 'autofilled-time'
          : ''
        }
        value={formatISODateForInput(message.timestamp)}
        onChange={handleTimestampChange}
      />

      {/* 4. 内容 */}
      <input
        type="text"
        className="text-input"
        placeholder="文本 / 媒体描述 / 系统消息..."
        value={message.text || ''}
        onChange={(e) => onChange('text', e.target.value)}
      />

      {/* 5. 控制按钮 */}
      <div className="message-controls">
        <div className="message-sort-controls-group">
          <button
            className="message-sort-btn"
            title="上移"
            onClick={() => onMove('up')}
            disabled={isFirstInGroup}
          >
            ↑
          </button>
          <button
            className="message-sort-btn"
            title="下移"
            onClick={() => onMove('down')}
            disabled={isLastInGroup}
          >
            ↓
          </button>
        </div>

        <button
          className="message-delete-btn"
          title="删除此条"
          onClick={onDelete}
        >
          &times;
        </button>
      </div>
    </div>
  );
}

export default EditableMessage;