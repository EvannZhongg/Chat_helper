import React, { useEffect, useState } from 'react';
// [新增] 导入 useNavigate
import { Link, useNavigate } from 'react-router-dom';
import { useProfileStore } from '../store/profileStore';
import ProfileForm from '../components/ProfileForm';

function ProfileList() {
  const { profiles, fetchProfiles, isLoading } = useProfileStore();
  const [showCreateForm, setShowCreateForm] = useState(false);

  // [新增] 初始化 navigate
  const navigate = useNavigate();

  useEffect(() => {
    fetchProfiles();
  }, [fetchProfiles]);

  const handleCreateProfile = async (data) => {
    // 1. 调用 store action
    const newProfile = await useProfileStore.getState().createProfile(data);

    // 2. [新增] 检查返回的 profile 并跳转
    if (newProfile && newProfile.profile_id) {
      navigate(`/profile/${newProfile.profile_id}`);
    } else {
      // 如果创建失败，表单不隐藏，提示用户
      alert("创建失败，请重试");
    }
  };

  if (isLoading && profiles.length === 0) {
    return <div>Loading...</div>;
  }

  return (
    <div>
      <h2>Profiles</h2>
      <button onClick={() => setShowCreateForm(!showCreateForm)} className={showCreateForm ? 'secondary' : ''}>
        {showCreateForm ? '取消新建' : '新建 Profile'}
      </button>

      {showCreateForm && (
        <ProfileForm
          // [修改] 调用新的 handler
          onSubmit={handleCreateProfile}
        />
      )}

      <hr />

      {/* [修改] 使用 className */}
      <div className="profile-list">
        {profiles.map((profile) => (
          <Link
            to={`/profile/${profile.profile_id}`}
            key={profile.profile_id}
            // [修改] 使用 className
            className="profile-card"
          >
            <strong>{profile.profile_name}</strong>
            <br />
            <span>({profile.user_name} vs {profile.opponent_name})</span>
          </Link>
        ))}
      </div>
    </div>
  );
}

export default ProfileList;