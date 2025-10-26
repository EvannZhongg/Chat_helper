import React, { useEffect, useState, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useProfileStore } from '../store/profileStore';
import ProfileForm from '../components/ProfileForm';

function ProfileList() {
  // 显式选择状态和 actions
  const profiles = useProfileStore(state => state.profiles);
  const fetchProfiles = useProfileStore(state => state.fetchProfiles);
  const isLoading = useProfileStore(state => state.isLoading);
  const createProfile = useProfileStore(state => state.createProfile);

  const [showCreateForm, setShowCreateForm] = useState(false);
  const navigate = useNavigate();

  // [修复] 使用 useCallback 封装 fetchProfiles 调用
  const stableFetchProfiles = useCallback(() => {
    if (typeof fetchProfiles === 'function') {
      fetchProfiles();
    } else {
      console.error("useEffect: fetchProfiles is not available yet, waiting for next render cycle.");
    }
  }, [fetchProfiles]);

  useEffect(() => {
    stableFetchProfiles(); // 首次挂载时调用封装函数
  }, [stableFetchProfiles]); // 依赖 memoized function

  const handleCreateProfile = async (data) => {
    if (typeof createProfile === 'function') {
        const newProfile = await createProfile(data);
        if (newProfile && newProfile.profile_id) {
          navigate(`/profile/${newProfile.profile_id}`);
        } else {
          alert("创建失败，请重试");
        }
    } else {
        console.error("handleCreateProfile: createProfile action is not available.");
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
          onSubmit={handleCreateProfile}
        />
      )}

      <hr />

      <div className="profile-list">
        {Array.isArray(profiles) && profiles.map((profile) => (
          <Link
            to={`/profile/${profile.profile_id}`}
            key={profile.profile_id}
            className="profile-card"
          >
            <strong>{profile.profile_name}</strong>
            <br />
            <span>({profile.user_name} vs {profile.opponent_name})</span>
          </Link>
        ))}
        {!isLoading && (!profiles || profiles.length === 0) && (
            <p>还没有 Profile，请点击上方按钮新建一个。</p>
        )}
      </div>
    </div>
  );
}

export default ProfileList;