// src/components/DateNodeGraph.jsx

import React, { useState } from 'react';
import { Handle, Position } from 'reactflow';

// Tooltip 组件 (保持不变)
function Tooltip({ content, isVisible }) {
  if (!isVisible) return null;
  // [!!] 确保 tooltip 在节点内部渲染，以便 CSS 控制其位置
  return <div className="graph-tooltip">{content}</div>;
}

function DateNodeGraph({ data }) {
  const [showTooltip, setShowTooltip] = useState(false);

  // 悬浮时显示的内容
  const tooltipContent = `记录: ${data.itemCount}${data.insightSummary ? `\n\n洞察:\n${data.insightSummary}` : ''}`;

  return (
    // [!!] 将事件监听器移到外层 div
    <div
      className="graph-node date-node"
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      {/* Tooltip 放在内部 */}
      <Tooltip content={tooltipContent} isVisible={showTooltip} />

      {/* 节点内容 */}
      <div className="node-content">
        <strong>{data.date}</strong>
        {/* 可以选择性地显示 item count */}
        {/* <div className="node-subtext">({data.itemCount}条)</div> */}
      </div>

      {/* 连接点 Handles (必须有！) */}
      {/* 允许从左侧连接（被上一个日期连接） */}
      <Handle
        type="target"
        position={Position.Left}
        id="date-in"
        style={{ top: '50%' }} // 确保垂直居中
      />
      {/* 允许从右侧连接（连接到下一个日期 或 详情节点） */}
      <Handle
        type="source"
        position={Position.Right}
        id="date-out"
        style={{ top: '50%' }} // 确保垂直居中
      />
    </div>
  );
}

export default DateNodeGraph;