import React, { useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useProfileStore } from '../store/profileStore';

function AnalysisPage() {
  const { profileId } = useParams();

  // 使用多个独立的 hooks 来避免选择器问题
  const currentProfile = useProfileStore(state => state.currentProfile);
  const isLoading = useProfileStore(state => state.isLoading);
  const insights = useProfileStore(state => state.insights);
  const isInsightLoading = useProfileStore(state => state.isInsightLoading);
  const analysisDateRange = useProfileStore(state => state.analysisDateRange);
  const isPersonaLoading = useProfileStore(state => state.isPersonaLoading);
  const analysisProgress = useProfileStore(state => state.analysisProgress);

  // 获取 actions
  const getProfile = useProfileStore(state => state.getProfile);
  const fetchInsights = useProfileStore(state => state.fetchInsights);
  const fetchDateRange = useProfileStore(state => state.fetchDateRange);
  const triggerFullAnalysis = useProfileStore(state => state.triggerFullAnalysis);

  // --- Hook 1: Fetch Primary Data (Profile) ---
  // 仅依赖 profileId。确保 Profile 是最新的。
  useEffect(() => {
    if (!profileId) return;

    // Fetch Profile only if currentProfile is null OR the ID does not match
    if (!currentProfile || currentProfile.profile_id !== profileId) {
        getProfile(profileId);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profileId, currentProfile?.profile_id]);

  // --- Hook 2: Fetch Secondary Data (Insights/Date Range) ---
  // 依赖 currentProfile。确保只有 Profile 加载成功后才开始获取其他数据。
  useEffect(() => {
    // 只有当 Profile 加载完成且 ID 匹配时才获取
    if (!currentProfile || currentProfile.profile_id !== profileId) return;

    // Fetch secondary data
    fetchDateRange(profileId);
    fetchInsights(profileId);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentProfile?.profile_id, profileId]);


  // 2. HANDLERS
  const handleStartAnalysis = () => {
    if (profileId) {
      triggerFullAnalysis(profileId);
    }
  };

  // 3. 条件渲染 (Hooks 之后)
  if (isLoading && !currentProfile) {
    return <div>Loading profile data...</div>;
  }
  if (!currentProfile) {
    return <div>Profile not found or failed to load.</div>;
  }

  // 4. RENDER
  return (
    <div>
      <Link to={`/profile/${profileId}`}>&lt; 返回 Profile 详情</Link>
      <h2>自动分析与洞察 for {currentProfile.profile_name}</h2>

      <div className="profile-form">
        <h4>触发增量分析</h4>
        <p>
          系统将自动分析从
          <strong> {analysisDateRange?.min_date || 'N/A'} </strong>
          到
          <strong> {analysisDateRange?.max_date || 'N/A'} </strong>
          之间所有未处理日期的聊天记录和事件。
        </p>
        <button
            onClick={handleStartAnalysis}
            // Button enabled only if min_date is available and not loading
            disabled={isPersonaLoading || !analysisDateRange?.min_date}
        >
          {isPersonaLoading ? "正在分析..." : "开始完整增量分析"}
        </button>
        {analysisProgress && (
          <p style={{ marginTop: '10px', color: isPersonaLoading ? '#007bff' : (analysisProgress.startsWith("分析失败") ? '#dc3545' : '#28a745') }}>
            状态: {analysisProgress}
          </p>
        )}
      </div>

      <h4 style={{ marginTop: '20px' }}>分析洞察 (Insights)</h4>
      {isInsightLoading && <div>(正在加载洞察列表...)</div>}
      {!isInsightLoading && (!insights || insights.length === 0) && (
        <p>(暂无分析洞察。请使用上方功能生成。)</p>
      )}
      <div className="profile-list">
        {insights && insights.map(insight => (
          <div key={insight.insight_id} className="profile-card" style={{ borderColor: '#eee' }}>
            <strong>
              分析日期: {insight.analysis_date}
            </strong>
            <p style={{ whiteSpace: 'pre-wrap', margin: '10px 0 0' }}>{insight.summary}</p>
            <small style={{ color: '#888' }}>
              处理记录数: {Array.isArray(insight.processed_item_ids) ? insight.processed_item_ids.length : 0}
            </small>
          </div>
        ))}
      </div>
    </div>
  );
}

export default AnalysisPage;