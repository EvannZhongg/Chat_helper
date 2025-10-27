// src/pages/TimelineGraphPage.jsx

import React, { useEffect, useState, useCallback, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  // addEdge, // [!!] 已移除未使用的 addEdge
  MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css'; // 引入 React Flow 样式

import { useProfileStore } from '../store/profileStore';
import DateNodeGraph from '../components/DateNodeGraph'; // [!!] 新的自定义日期节点
import DetailNodeGraph from '../components/DetailNodeGraph'; // [!!] 新的自定义详情节点

// 布局常量 (保持不变)
const NODE_WIDTH = 180; // (圆形节点宽度在 CSS 中定义)
const NODE_HEIGHT = 60; // (圆形节点高度在 CSS 中定义)
const VERTICAL_GAP = 100;
const DETAIL_OFFSET_X = 250;
const DETAIL_VERTICAL_GAP = 20;

function TimelineGraphPage() {
  const { profileId } = useParams();

  // 1. 从 Zustand 获取数据 (保持不变)
  const timelineData = useProfileStore(state => state.timelineData);
  const isTimelineLoading = useProfileStore(state => state.isTimelineLoading);
  const fetchTimelineData = useProfileStore(state => state.fetchTimelineData);
  const clearTimelineData = useProfileStore(state => state.clearTimelineData);

  // 2. 使用 React Flow 的 hooks 管理节点和边 (保持不变)
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  // 3. 本地 state 跟踪被展开的日期节点 ID (保持不变)
  const [expandedNodeId, setExpandedNodeId] = useState(null);

  // 4. 加载数据 (保持不变)
  useEffect(() => {
    if (profileId) {
      fetchTimelineData(profileId);
    }
    return () => {
      clearTimelineData();
      setNodes([]); // 清空节点
      setEdges([]); // 清空边
      setExpandedNodeId(null);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profileId]);

  // 5. [核心] 将后端数据转换为 React Flow 格式 (修改边的 type)
  useEffect(() => {
    if (!timelineData || timelineData.length === 0) {
      setNodes([]);
      setEdges([]);
      return;
    }

    const initialNodes = [];
    const initialEdges = [];

    // 计算日期节点位置并创建
    timelineData.forEach((dateNode, index) => {
      initialNodes.push({
        id: dateNode.date, // 使用日期作为唯一 ID
        type: 'dateNode', // [!!] 指定使用自定义节点类型
        data: {
          date: dateNode.date,
          itemCount: dateNode.item_count,
          insightSummary: dateNode.insight_summary,
        },
        // [!!] 圆形节点的位置可能需要微调 Y 轴间距以适应新的尺寸
        position: { x: 0, y: index * (90 + VERTICAL_GAP + 20) }, // 假设圆形节点直径90px, 增加一点间距
      });

      // 创建连接上一个日期节点的边
      if (index > 0) {
        const prevDate = timelineData[index - 1].date;
        initialEdges.push({
          id: `e-${prevDate}-to-${dateNode.date}`,
          source: prevDate, // 上一个节点的 ID
          target: dateNode.date, // 当前节点的 ID
          type: 'bezier',      // [!!] 修改: 使用贝塞尔曲线
          markerEnd: { type: MarkerType.ArrowClosed }, // 箭头
        });
      }
    });

    setNodes(initialNodes);
    setEdges(initialEdges);

  }, [timelineData, setNodes, setEdges]);


  // 6. [核心] 处理节点点击事件 (展开/折叠) (修改边的 type)
  const onNodeClick = useCallback((event, node) => {
    if (node.type !== 'dateNode') return; // 只处理日期节点的点击

    const clickedNodeId = node.id;

    setNodes(prevNodes => {
      // 检查是否重复点击已展开的节点（收起）
      if (expandedNodeId === clickedNodeId) {
        setExpandedNodeId(null);
        // 移除所有详情节点和相关边
        setEdges(prevEdges => prevEdges.filter(e => e.id.startsWith('e-') && !e.id.includes('-to-chat') && !e.id.includes('-to-events'))); // [!!] 确保在 setNodes 前更新 edges
        return prevNodes.filter(n => n.type === 'dateNode');
      }

      // --- 展开新节点 ---
      setExpandedNodeId(clickedNodeId);

      // 先移除旧的详情节点（如果有）
      const baseNodes = prevNodes.filter(n => n.type === 'dateNode');

      // 找到被点击的日期节点在 timelineData 中的数据
      const dateNodeData = timelineData.find(d => d.date === clickedNodeId);
      if (!dateNodeData || !dateNodeData.items) return baseNodes; // 防御性编程

      const detailNodes = [];
      const detailEdges = [];

      // 分离消息和事件
      const messages = dateNodeData.items.filter(item => item.item_type === 'message');
      const events = dateNodeData.items.filter(item => item.item_type === 'event');

      // --- 创建“聊天细节”节点 ---
      if (messages.length > 0) {
          const chatId = `${clickedNodeId}-messages`;
          detailNodes.push({
              id: chatId,
              type: 'detailNode', // [!!] 使用详情节点类型
              data: { title: '聊天记录', items: messages },
              position: {
                  x: node.position.x + DETAIL_OFFSET_X,
                  // [!!] 微调 Y 位置，使其与圆形节点中心大致对齐
                  y: node.position.y - 50 // 假设详情节点高度约 200px
              },
          });
          detailEdges.push({
              id: `e-${clickedNodeId}-to-chat`,
              source: clickedNodeId,
              target: chatId,
              type: 'bezier',      // [!!] 修改: 使用贝塞尔曲线
          });
      }

      // --- 创建“事件”节点 ---
      if (events.length > 0) {
          const eventId = `${clickedNodeId}-events`;
          // 计算事件节点的 Y 位置，使其在聊天节点下方（如果有聊天节点）
          const eventNodeY = messages.length > 0
              ? (node.position.y - 50) + 200 // 假设聊天节点高度200px
              : (node.position.y - 50); // 与聊天节点起始位置对齐

          detailNodes.push({
              id: eventId,
              type: 'detailNode',
              data: { title: '离线事件', items: events },
              position: {
                  x: node.position.x + DETAIL_OFFSET_X,
                  y: eventNodeY + (messages.length > 0 ? DETAIL_VERTICAL_GAP : 0),
              },
          });
          detailEdges.push({
              id: `e-${clickedNodeId}-to-events`,
              source: clickedNodeId,
              target: eventId,
              type: 'bezier',      // [!!] 修改: 使用贝塞尔曲线
          });
      }

      // 更新边 (只保留日期之间的边和新展开的详情边)
      setEdges(prevEdges => [
          ...prevEdges.filter(e => e.id.startsWith('e-') && !e.id.includes('-to-chat') && !e.id.includes('-to-events')), // 保留日期连接线
          ...detailEdges // 添加新的详情连接线
      ]);

      // 返回基础日期节点 + 新的详情节点
      return [...baseNodes, ...detailNodes];
    });
  }, [expandedNodeId, timelineData, setNodes, setEdges]); // 依赖项

  // 7. 定义自定义节点类型 (保持不变)
  const nodeTypes = useMemo(() => ({
    dateNode: DateNodeGraph,
    detailNode: DetailNodeGraph,
  }), []);

  return (
    <div>
      <Link to={`/profile/${profileId}`}>&lt; 返回 Profile 详情</Link>
      <h2>沟通时间线 (图谱视图)</h2>

      {isTimelineLoading && <div style={{marginTop: '20px'}}>正在加载时间线数据...</div>}

      {/* 设置 ReactFlow 画布高度 */}
      <div style={{ height: '70vh', border: '1px solid #eee', marginTop: '15px' }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          // onConnect={onConnect} // 如果需要手动连接可以启用
          nodeTypes={nodeTypes} // [!!] 注册自定义节点
          onNodeClick={onNodeClick} // [!!] 监听节点点击
          fitView // 自动缩放以适应所有节点
          // [!!] 可以添加一些默认的边选项
          defaultEdgeOptions={{
            type: 'bezier', // 默认使用贝塞尔曲线
            animated: false, // 可以设为 true 增加流动效果
            style: { strokeWidth: 2 },
          }}
          // [!!] 可以添加连接线样式
          connectionLineStyle={{ stroke: '#adb5bd', strokeWidth: 2 }}
        >
          <Background />
          <Controls />
          <MiniMap />
        </ReactFlow>
      </div>
    </div>
  );
}

export default TimelineGraphPage;