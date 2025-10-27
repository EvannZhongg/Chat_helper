// src/components/DetailNodeGraph.jsx

import React from 'react';
import { Handle, Position } from 'reactflow';

// 辅助函数：格式化时间戳为 HH:MM (和之前 TimelineNode 一样)
function formatTime(isoTimestamp) {
  try {
    const date = new Date(isoTimestamp);
    // 使用 UTC 避免本地偏移
    const hours = date.getUTCHours().toString().padStart(2, '0');
    const minutes = date.getUTCMinutes().toString().padStart(2, '0');
    return `${hours}:${minutes}`;
  } catch (e) { return "??:??"; }
}

function DetailNodeGraph({ data }) {
  const { title, items } = data;

  return (
    <div className="graph-node detail-node">
      {/* 节点标题 */}
      <div className="detail-node-title">{title} ({items.length}条)</div>

      {/* 节点内容 (滚动列表) */}
      <div className="detail-node-content">
        {items.map(item => (
          <div
            key={item.data.message_id || item.data.event_id}
            className={`detail-item ${item.item_type === 'event' ? 'detail-item-event' : 'detail-item-message'}`}
          >
            <span className="detail-item-time">{formatTime(item.timestamp)}</span>
            {item.item_type === 'event' ? (
              <span className="detail-item-text">
                <span className="detail-tag event-tag">[事件]</span> {item.data.summary}
              </span>
            ) : (
              <span className="detail-item-text">
                 <span className={`detail-tag sender-tag type-${item.data.sender}`}>
                   {item.data.sender === 'User 1' ? '我' : (item.data.sender === 'User 2' ? '对方' : '系统')}
                 </span>{' '}
                 {item.data.text || `[${item.data.content_type}]`}
              </span>
            )}
          </div>
        ))}
      </div>

      {/* 连接点 Handle (必须有！) */}
      {/* 允许从左侧连接（被日期节点连接） */}
      <Handle type="target" position={Position.Left} id="detail-in" />
    </div>
  );
}

export default DetailNodeGraph;