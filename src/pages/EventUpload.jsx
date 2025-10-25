import React, { useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import apiClient from '../api/apiClient';

function EventUpload() {
  const { profileId } = useParams();
  const navigate = useNavigate();

  // 阶段 1：用户输入
  const [description, setDescription] = useState('');
  const [imageFile, setImageFile] = useState(null);

  // 阶段 2：分析结果
  const [analysisResult, setAnalysisResult] = useState({
    summary: '',
    original_image_hash: null,
  });
  const [eventTimestamp, setEventTimestamp] = useState('');

  // 状态
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [step, setStep] = useState(1); // 1: 输入, 2: 确认

  const handleFileChange = (e) => {
    setImageFile(e.target.files[0] || null);
  };

  // --- API 1: 分析事件 ---
  const handleAnalyze = async () => {
    if (!description && !imageFile) {
      alert("请输入事件描述或上传一张图片。");
      return;
    }
    setIsLoading(true);

    const formData = new FormData();
    if (description) {
      formData.append('description', description);
    }
    if (imageFile) {
      formData.append('file', imageFile);
    }

    try {
      const response = await apiClient.post(
        `/events/${profileId}/analyze`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );

      setAnalysisResult(response.data); // { summary, original_image_hash }

      // 自动填充当前时间，并标红
      setEventTimestamp(new Date().toISOString().slice(0, 16));

      setStep(2); // 进入确认阶段
    } catch (error) {
      console.error("Event analysis failed:", error);
      alert("分析失败: " + (error.response?.data?.detail || error.message));
    } finally {
      setIsLoading(false);
    }
  };

  // --- API 2: 保存事件 ---
  const handleSave = async () => {
    if (!analysisResult.summary || !eventTimestamp) {
      alert("摘要和时间戳不能为空。");
      return;
    }
    setIsSaving(true);

    try {
      const requestBody = {
        summary: analysisResult.summary, // 用户可能编辑过的
        timestamp: new Date(eventTimestamp).toISOString(),
        original_text: description,
        original_image_hash: analysisResult.original_image_hash
      };

      await apiClient.post(`/events/${profileId}/save`, requestBody);

      alert('事件保存成功!');
      navigate(`/profile/${profileId}`); // 保存成功后返回详情页

    } catch (error) {
      console.error("Event save failed:", error);
      alert("保存失败: " + (error.response?.data?.detail || error.message));
    } finally {
      setIsSaving(false);
    }
  };

  // 辅助：当用户编辑摘要时
  const handleSummaryChange = (e) => {
    setAnalysisResult(prev => ({ ...prev, summary: e.target.value }));
  };

  return (
    <div>
      <Link to={`/profile/${profileId}`}>&lt; 返回 Profile 详情</Link>
      <h3>上传离线事件</h3>

      {/* --- 阶段 1: 输入表单 --- */}
      <div className="profile-form" style={{ display: step === 1 ? 'block' : 'none' }}>
        <div className="form-group">
          <label>事件描述 (可选, 您的“想法描述”)</label>
          <textarea
            rows="5"
            placeholder="例如：今天线下开会，老板批评了项目进展..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }}
          ></textarea>
        </div>

        <div className="form-group">
          <label>相关图片 (可选)</label>
          <input
            type="file"
            accept="image/*"
            onChange={handleFileChange}
          />
        </div>

        <button onClick={handleAnalyze} disabled={isLoading}>
          {isLoading ? '正在分析...' : '分析事件'}
        </button>
      </div>

      {/* --- 阶段 2: 确认表单 --- */}
      <div className="profile-form" style={{ display: step === 2 ? 'block' : 'none' }}>
        <div className="form-group">
          <label>事件摘要 (模型已生成，可编辑)</label>
          <textarea
            rows="5"
            value={analysisResult.summary}
            onChange={handleSummaryChange}
            style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }}
          ></textarea>
        </div>

        <div className="form-group">
          <label>事件发生时间 (必填)</label>
          <input
            type="datetime-local"
            className="autofilled-time" // 默认为红色
            value={eventTimestamp}
            onChange={(e) => setEventTimestamp(e.target.value)}
          />
        </div>

        <button onClick={handleSave} disabled={isSaving}>
          {isSaving ? '保存中...' : '确认并保存事件'}
        </button>
        <button
          onClick={() => setStep(1)}
          className="secondary"
          style={{ marginLeft: '10px' }}
        >
          &lt; 返回修改
        </button>
      </div>
    </div>
  );
}

export default EventUpload;