import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useProfileStore } from '../store/profileStore';
import ProfileForm from '../components/ProfileForm';

// 辅助函数
function getLocalDateForInput(date = new Date()) {
    const offset = date.getTimezoneOffset();
    const localDate = new Date(date.getTime() - (offset * 60000));
    return localDate.toISOString().slice(0, 16);
}

function ProfileDetail() {
  const { profileId } = useParams(); // Hook 1

  // --- [关键修复] 所有 Hooks 调用移到最前面 ---
  // 1. 单独选择数据状态
  const currentProfile = useProfileStore(state => state.currentProfile); // Hook 2
  const currentUserPersona = useProfileStore(state => state.currentUserPersona); // Hook 3
  const currentOpponentPersona = useProfileStore(state => state.currentOpponentPersona); // Hook 4

  // 2. 单独选择加载状态
  const isLoading = useProfileStore(state => state.isLoading); // Hook 5
  const isPersonaLoading = useProfileStore(state => state.isPersonaLoading); // Hook 6

  // 3. 单独选择 actions
  const getProfile = useProfileStore(state => state.getProfile); // Hook 7
  const fetchPersonas = useProfileStore(state => state.fetchPersonas); // Hook 8
  const updateUserPersona = useProfileStore(state => state.updateUserPersona); // Hook 9
  const updateOpponentPersona = useProfileStore(state => state.updateOpponentPersona); // Hook 10
  const updateProfileNames = useProfileStore(state => state.updateProfileNames); // Hook 11

  // [!!] 从 AnalysisPage.jsx 移回来的 Hooks，用于 ProfileDetail
  const fetchDateRange = useProfileStore(state => state.fetchDateRange);
  const fetchInsights = useProfileStore(state => state.fetchInsights);


  // --- 本地状态 ---
  const [isEditing, setIsEditing] = useState(false); // Hook 12
  const [userPersonaInput, setUserPersonaInput] = useState(''); // Hook 13
  const [opponentPersonaInput, setOpponentPersonaInput] = useState(''); // Hook 14

  // --- Effects ---
  useEffect(() => { // Hook 15
    if (profileId) {
        getProfile(profileId);
        fetchPersonas(profileId);
    }
    // Cleanup function
    return () => {
        // (cleanup)
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profileId]); // <-- 只依赖 profileId

  // [!!] 新增 Effect: 当 profile 加载成功后，获取 insights 和 daterange
  // (这在 AnalysisPage 中也有，但放在这里可以为其他组件预热)
  useEffect(() => {
    if (!currentProfile || currentProfile.profile_id !== profileId) return;
    fetchDateRange(profileId);
    fetchInsights(profileId);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentProfile?.profile_id, profileId]);


  // --- [关键修复] 条件渲染逻辑现在位于所有 Hooks 调用之后 ---
  if (isLoading && !currentProfile) {
     return <div>Loading profile...</div>;
  }
  const storeProfileId = useProfileStore.getState().currentProfile?.profile_id;
  if (!isLoading && !currentProfile && profileId === storeProfileId) {
      return <div>Profile not found or failed to load.</div>;
  }
  if (!currentProfile) {
     return <div>Loading...</div>; // 或者返回 null
  }

  // --- Handlers (在 Hooks 和条件返回之后定义) ---
  const handleUpdateNames = (data) => {
    updateProfileNames(profileId, data);
    setIsEditing(false);
  };

  const handleUpdateUserPersona = () => {
    if (!userPersonaInput) return alert("请输入描述");
    updateUserPersona(profileId, userPersonaInput);
    setUserPersonaInput('');
  };

  const handleUpdateOpponentPersona = () => {
    if (!opponentPersonaInput) return alert("请输入描述");
    updateOpponentPersona(profileId, opponentPersonaInput);
    setOpponentPersonaInput('');
  };
  // --- End Handlers ---

  // --- JSX ---
  return (
    <div>
      <Link to="/">&lt; 返回列表</Link>

      {/* --- [新增] 标题和时间线按钮 --- */}
      <div className="profile-header-actions">
        <h2>{currentProfile.profile_name}</h2>
        <Link to={`/profile/${profileId}/timeline`}>
          <button className="timeline-nav-btn">
            查看时间线
          </button>
        </Link>
      </div>
      {/* --- 修改结束 --- */}


      {/* --- 操作选项 --- */}
      <h3>操作选项</h3>
      <nav className="nav-links">
        <Link to={`/profile/${profileId}/upload`}>
          <button>上传聊天截图 (Phase 1)</button>
        </Link>
        <Link to={`/profile/${profileId}/events/new`}>
          <button className="secondary">上传离线事件</button>
        </Link>
        <Link to={`/profile/${profileId}/analyze`}>
            <button>自动分析与洞察 (Phase 2)</button>
        </Link>
        <Link to={`/profile/${profileId}/assist`}> {/* 激活 Phase 3 按钮 */}
            <button>对话辅助 (Phase 3)</button>
        </Link>
      </nav>

      <hr />

      {/* --- Profile 设置 --- */}
      <h3>Profile 设置</h3>
      <button onClick={() => setIsEditing(!isEditing)} className={isEditing ? 'secondary' : ''}>
        {isEditing ? '取消修改' : '修改名称'}
      </button>
      {isEditing && (
        <ProfileForm
          onSubmit={handleUpdateNames}
          initialData={{
            profile_name: currentProfile.profile_name,
            user_name: currentProfile.user_name,
            opponent_name: currentProfile.opponent_name
          }}
          submitText="保存修改"
        />
      )}

      <hr />

      {/* --- 画像设置 (手动) --- */}
      <h3>画像设置 (手动)</h3>
      {isPersonaLoading && <div>(正在加载或更新画像...)</div>}
      {!isPersonaLoading && (
          <>
            <div className="profile-form">
                <h4>我的画像 (User Persona)</h4>
                {currentUserPersona?.self_summary ? (
                <div style={{ padding: '10px', background: '#f0f0f0', borderRadius: '4px', marginBottom: '10px', whiteSpace: 'pre-wrap' }}>
                    <strong>当前总结:</strong>
                    <p style={{ margin: '5px 0 0' }}>{currentUserPersona.self_summary}</p>
                </div>
                ) : <p>(暂无总结，请在下方输入描述并更新)</p>}
                <div className="form-group">
                <label>更新我的描述 (性格, MBTI, 沟通风格...):</label>
                <textarea
                    rows="3"
                    value={userPersonaInput}
                    onChange={(e) => setUserPersonaInput(e.target.value)}
                    placeholder="例如：我的MBTI是INTJ，性格比较直接，不希望在沟通中浪费时间..."
                    style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }}
                ></textarea>
                </div>
                <button onClick={handleUpdateUserPersona} disabled={isPersonaLoading}>
                {isPersonaLoading ? "..." : "更新“我”的画像"}
                </button>
            </div>

            <div className="profile-form" style={{ marginTop: '15px' }}>
                <h4>对方画像 (Opponent Persona)</h4>
                {currentOpponentPersona?.basic_info && Object.keys(currentOpponentPersona.basic_info).length > 0 ? (
                <div style={{ padding: '10px', background: '#f0f0f0', borderRadius: '4px', marginBottom: '10px' }}>
                    <strong>当前基础信息:</strong>
                    <ul style={{ margin: '5px 0 0', paddingLeft: '20px' }}>
                    {Object.entries(currentOpponentPersona.basic_info).map(([key, value]) => (
                        <li key={key}><strong>{key}:</strong> {value}</li>
                    ))}
                    </ul>
                </div>
                 ) : <p>(暂无基础信息，请在下方输入描述并更新)</p>}
                <div className="form-group">
                <label>添加对方的基础信息 (联系方式, 地址, 背景...):</label>
                <textarea
                    rows="3"
                    value={opponentPersonaInput}
                    onChange={(e) => setOpponentPersonaInput(e.target.value)}
                    placeholder="例如：他的电话是 13800138000。地址在XX大厦。他是CEO的侄子。"
                    style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }}
                ></textarea>
                </div>
                <button onClick={handleUpdateOpponentPersona} disabled={isPersonaLoading}>
                {isPersonaLoading ? "..." : "更新“对方”画像"}
                </button>
            </div>
          </>
      )}
    </div>
  );
}

export default ProfileDetail;