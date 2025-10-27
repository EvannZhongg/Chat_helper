import { create } from 'zustand';
import apiClient from '../api/apiClient';

export const useProfileStore = create((set, get) => ({
  profiles: [],
  currentProfile: null,
  isLoading: false,

  // --- [Phase 2: New States] ---
  currentUserPersona: null,
  currentOpponentPersona: null,
  isPersonaLoading: false,
  insights: [],
  isInsightLoading: false,
  analysisDateRange: { min_date: null, max_date: null },
  analysisProgress: null,
  isAssisting: false,
  assistResult: null,
  // --- [新增] Timeline States ---
  timelineData: [],
  isTimelineLoading: false,

  // --- Main Profile Actions (Original, untouched) ---

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
    if (get().currentProfile?.profile_id !== profileId) {
        set({ currentProfile: null });
    }
    try {
      const response = await apiClient.get(`/profiles/${profileId}`);
      set({ currentProfile: response.data, isLoading: false });
      return response.data;
    } catch (error) {
      console.error("Failed to get profile:", error);
      set({ isLoading: false, currentProfile: null });
    }
  },

  // [优化后] 创建Profile
  createProfile: async (profileData) => {
    set({ isLoading: true });
    try {
      const response = await apiClient.post('/profiles/', profileData);
      const newProfile = response.data;
      set(state => ({
        profiles: [newProfile, ...state.profiles],
        isLoading: false
      }));
      return newProfile;
    } catch (error) {
      console.error("Failed to create profile:", error);
      set({ isLoading: false });
      return null;
    }
  },

  // [优化后] 更新Profile
  updateProfileNames: async (profileId, nameData) => {
    set({ isLoading: true });
    try {
      const response = await apiClient.patch(`/profiles/${profileId}`, nameData);
      const updatedProfile = response.data;
      set(state => ({
        currentProfile: updatedProfile,
        profiles: state.profiles.map(p =>
          p.profile_id === profileId ? updatedProfile : p
        ),
        isLoading: false
      }));
    } catch (error) {
      console.error("Failed to update profile:", error);
      set({ isLoading: false });
    }
  },

  // --- [Phase 2: New Actions] ---

  fetchPersonas: async (profileId) => {
    set({ isPersonaLoading: true });
    if (get().currentUserPersona?.profile_id !== profileId && get().currentOpponentPersona?.profile_id !== profileId) {
         set({ currentUserPersona: null, currentOpponentPersona: null });
     }
    try {
      const [userRes, oppRes] = await Promise.allSettled([
        apiClient.get(`/persona/${profileId}/user`),
        apiClient.get(`/persona/${profileId}/opponent`)
      ]);
      const update = {};
      update.currentUserPersona = userRes.status === 'fulfilled' ? userRes.value.data : null;
      update.currentOpponentPersona = oppRes.status === 'fulfilled' ? oppRes.value.data : null;
      set(update);
    } catch (error) {
       console.error("Failed to fetch personas:", error);
       set({ currentUserPersona: null, currentOpponentPersona: null });
    } finally {
      set({ isPersonaLoading: false });
    }
  },

  updateUserPersona: async (profileId, description) => {
    set({ isPersonaLoading: true });
    try {
      const response = await apiClient.post(`/persona/${profileId}/user`, { description });
      set({ currentUserPersona: response.data, isPersonaLoading: false });
    } catch (error) {
      console.error("Failed to update user persona:", error);
      alert("更新用户画像失败: " + (error.response?.data?.detail || error.message));
      set({ isPersonaLoading: false });
    }
  },

  updateOpponentPersona: async (profileId, description) => {
    set({ isPersonaLoading: true });
    try {
      const response = await apiClient.post(`/persona/${profileId}/opponent`, { description });
      set({ currentOpponentPersona: response.data, isPersonaLoading: false });
    } catch (error) {
      console.error("Failed to update opponent persona:", error);
      alert("更新对方画像失败: " + (error.response?.data?.detail || error.message));
      set({ isPersonaLoading: false });
    }
  },

  fetchInsights: async (profileId) => {
    set({ isInsightLoading: true });
     if (get().insights?.length > 0 && get().insights[0]?.profile_id !== profileId) {
         set({ insights: [] });
    }
    try {
      const response = await apiClient.get(`/persona/${profileId}/insights`);
      set({ insights: response.data, isInsightLoading: false });
    } catch (error) {
      if (error.response?.status !== 404) {
        console.error("Failed to fetch insights:", error);
      }
      set({ insights: [], isInsightLoading: false });
    }
  },

  fetchDateRange: async (profileId) => {
      set({ analysisDateRange: { min_date: null, max_date: null } });
      try {
        const response = await apiClient.get(`/persona/${profileId}/date_range`);
        set({ analysisDateRange: response.data });
      } catch (error) {
        console.error("Failed to fetch date range:", error);
      }
    },

  triggerFullAnalysis: async (profileId) => {
      if (!window.confirm("这将分析所有未处理的日期，可能需要一些时间并消耗较多Token。确定继续吗？")) {
        return;
      }
      set({ isPersonaLoading: true, analysisProgress: "开始分析..." });
      try {
        const response = await apiClient.post(`/persona/${profileId}/analyze_all`);
        const result = response.data;

        alert(result.message);
        set({ analysisProgress: result.message });

        get().fetchPersonas(profileId);
        get().fetchInsights(profileId);

         set({ isPersonaLoading: false });


      } catch (error) {
        console.error("Failed to trigger full analysis:", error);
        const errorMsg = error.response?.data?.detail || error.message;
        alert("分析失败: " + errorMsg);
        set({ isPersonaLoading: false, analysisProgress: "分析失败: " + errorMsg });
      }
    },

  // --- [Phase 3: New Actions] ---
  getAssistance: async (profileId, opponent_message, user_thoughts) => {
    set({ isAssisting: true, assistResult: null });
    try {
      const response = await apiClient.post(`/assist/${profileId}`, {
        opponent_message,
        user_thoughts
      });
      set({ assistResult: response.data, isAssisting: false });
    } catch (error) {
      console.error("Failed to get assistance:", error);
      alert("获取建议失败: " + (error.response?.data?.detail || error.message));
      set({ isAssisting: false });
    }
  },

  clearAssistResult: () => {
    set({ assistResult: null });
  },

  // --- [新增] Timeline Actions ---
  fetchTimelineData: async (profileId) => {
    set({ isTimelineLoading: true, timelineData: [] });
    try {
      const response = await apiClient.get(`/timeline/${profileId}`);
      set({ timelineData: response.data, isTimelineLoading: false });
    } catch (error) {
      console.error("Failed to fetch timeline data:", error);
      alert("加载时间线失败: " + (error.response?.data?.detail || error.message));
      set({ isTimelineLoading: false });
    }
  },

  clearTimelineData: () => {
    set({ timelineData: [] });
  },

}));