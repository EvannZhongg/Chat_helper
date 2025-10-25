import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom'; // 移除 useNavigate，这里不需要了
import { useProfileStore } from '../store/profileStore';
import ProfileForm from '../components/ProfileForm';

function ProfileDetail() {
  const { profileId } = useParams();
  // 移除 navigate
  const { currentProfile, getProfile, isLoading } = useProfileStore();
  const [isEditing, setIsEditing] = useState(false);

  useEffect(() => {
    if (profileId) {
      getProfile(profileId);
    }
  }, [profileId, getProfile]);

  if (isLoading || !currentProfile) {
    return <div>Loading profile...</div>;
  }

  const handleUpdateNames = (data) => {
    useProfileStore.getState().updateProfileNames(profileId, data);
    setIsEditing(false);
  };

  return (
    <div>
      <Link to="/">&lt; 返回列表</Link>
      <h2>{currentProfile.profile_name}</h2>

      <h3>操作选项</h3>
      {/* [修改] 使用 className */}
      <nav className="nav-links">
        <Link to={`/profile/${profileId}/upload`}>
          <button>上传聊天截图 (Phase 1)</button>
        </Link>

        <Link to={`/profile/${profileId}/events/new`}>
          <button className="secondary">上传离线事件</button>
        </Link>
        <button disabled>分析画像 (Phase 2)</button>
        <button disabled>对话辅助 (Phase 3)</button>
      </nav>

      <hr />

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
    </div>
  );
}

export default ProfileDetail;