import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useProfileStore } from '../store/profileStore';

function AssistPage() {
  const { profileId } = useParams();

  // 1. 从 Zustand 获取状态和 Action
  const isAssisting = useProfileStore(state => state.isAssisting);
  const assistResult = useProfileStore(state => state.assistResult);
  const getAssistance = useProfileStore(state => state.getAssistance);
  const clearAssistResult = useProfileStore(state => state.clearAssistResult);

  // 2. 本地状态管理两个输入框
  const [opponentMessage, setOpponentMessage] = useState('');
  const [userThoughts, setUserThoughts] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!opponentMessage && !userThoughts) {
      alert('至少需要输入“对方的消息”或“你的想法”之一');
      return;
    }
    getAssistance(profileId, opponentMessage, userThoughts);
  };

  // 离开页面时清空结果
  React.useEffect(() => {
    return () => {
      clearAssistResult();
    };
  }, [clearAssistResult]);

  return (
    <div>
      <Link to={`/profile/${profileId}`}>&lt; 返回 Profile 详情</Link>
      <h2>对话辅助 (Phase 3)</h2>

      {/* --- 输入表单 --- */}
      <form onSubmit={handleSubmit} className="profile-form">
        <div className="form-group">
          <label>"对方" 的最新消息 (选填)</label>
          <textarea
            rows="3"
            value={opponentMessage}
            onChange={(e) => setOpponentMessage(e.target.value)}
            placeholder="例如：你上次说的那个报告怎么样了？"
            style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }}
          ></textarea>
        </div>
        <div className="form-group">
          <label>"我" 内心的真实想法 (必填)</label>
          <textarea
            rows="3"
            value={userThoughts}
            onChange={(e) => setUserThoughts(e.target.value)}
            placeholder="例如：完了，我还没做，但又不想让他觉得我不靠谱..."
            style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }}
          ></textarea>
        </div>
        <button type="submit" disabled={isAssisting || !userThoughts}>
          {isAssisting ? '军师思考中...' : '获取回复建议'}
        </button>
      </form>

      {/* --- 结果展示 --- */}
      {isAssisting && <p style={{marginTop: '20px'}}>正在生成建议...</p>}

      {assistResult && (
        <div style={{marginTop: '20px'}}>
          <h3>策略分析</h3>
          <div className="profile-card" style={{background: '#fdfdfd'}}>
             <p style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{assistResult.strategy_analysis}</p>
          </div>

          <h3 style={{marginTop: '20px'}}>回复选项</h3>
          <div className="profile-list">
            {assistResult.reply_options.map((option, index) => (
              <div key={index} className="profile-card" style={{borderColor: '#eee'}}>
                <p style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{option}</p>
                {/* (未来可以加一个“复制”按钮) */}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default AssistPage;