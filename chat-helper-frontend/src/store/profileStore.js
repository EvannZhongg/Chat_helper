import { create } from 'zustand';
import apiClient from '../api/apiClient';

export const useProfileStore = create((set, get) => ({
  profiles: [],
  currentProfile: null,
  isLoading: false,

  // 获取所有Profiles
  fetchProfiles: async () => {
    set({ isLoading: true });
    try {
      const response = await apiClient.get('/profiles/');
      set({ profiles: response.data, isLoading: false });
    } catch (error) {
      console.error("Failed to fetch profiles:", error);
      set({ isLoading: false });
    }
  },

  // 获取单个Profile
  getProfile: async (profileId) => {
    set({ isLoading: true });
    try {
      const response = await apiClient.get(`/profiles/${profileId}`);
      set({ currentProfile: response.data, isLoading: false });
      return response.data;
    } catch (error) {
      console.error("Failed to get profile:", error);
      set({ isLoading: false });
    }
  },

  // [优化后] 创建Profile
  createProfile: async (profileData) => {
    set({ isLoading: true });
    try {
      const response = await apiClient.post('/profiles/', profileData);
      const newProfile = response.data;

      // [FIX] 不再调用 fetchProfiles()，而是手动将新 Profile 添加到状态中
      set(state => ({
        profiles: [newProfile, ...state.profiles], // 在列表顶部添加
        isLoading: false // 在这里设置 false
      }));
      return newProfile;

    } catch (error) {
      console.error("Failed to create profile:", error);
      set({ isLoading: false }); // 确保在出错时也设置 false
      return null;
    }
    // [FIX] 移除了 'finally' 块，因为 try/catch 都处理了 state
  },

  // [优化后] 更新Profile
  updateProfileNames: async (profileId, nameData) => {
    set({ isLoading: true });
    try {
      const response = await apiClient.patch(`/profiles/${profileId}`, nameData);
      const updatedProfile = response.data;

      // [FIX] 不再调用 fetchProfiles()，而是手动更新状态
      set(state => ({
        currentProfile: updatedProfile,
        // 同时更新列表中的那一个
        profiles: state.profiles.map(p =>
          p.profile_id === profileId ? updatedProfile : p
        ),
        isLoading: false // 在这里设置 false
      }));
    } catch (error) {
      console.error("Failed to update profile:", error);
      set({ isLoading: false }); // 确保在出错时也设置 false
    }
  },
}));