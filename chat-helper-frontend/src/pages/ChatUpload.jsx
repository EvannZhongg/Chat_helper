import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useProfileStore } from '../store/profileStore';
import apiClient from '../api/apiClient';
import EditableMessage from '../components/EditableMessage';

function ChatUpload() {
  const { profileId } = useParams();
  const { currentProfile, getProfile } = useProfileStore();

  const [files, setFiles] = useState([]);
  const [editableMessages, setEditableMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [totalUsage, setTotalUsage] = useState(null);

  useEffect(() => {
    if (profileId) {
      getProfile(profileId);
    }
  }, [profileId, getProfile]);

  const handleFileChange = (e) => {
    setFiles(Array.from(e.target.files));
  };

  // 满足“依次分析”需求，并在UI上显示
  const handleVLMUpload = async () => {
    if (files.length === 0) return;
    setIsLoading(true);
    setEditableMessages([]);
    setTotalUsage(null);

    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file); // 后端API支持批量
    });

    try {
      const response = await apiClient.post(
        `/import/${profileId}/upload_screenshots`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );

      const { results, total_usage } = response.data;

      // 将所有图片的解析结果合并为一个列表
      const allMessages = results.flatMap(result => result.messages);

      // 按时间戳排序
      allMessages.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

      setEditableMessages(allMessages);
      setTotalUsage(total_usage);

    } catch (error) {
      console.error("VLM upload failed:", error);
      alert("解析失败: " + (error.response?.data?.detail || error.message));
    } finally {
      setIsLoading(false);
    }
  };

  // 处理单条消息的编辑
  const handleMessageChange = (index, field, value) => {
    const updatedMessages = [...editableMessages];
    updatedMessages[index] = { ...updatedMessages[index], [field]: value };
    setEditableMessages(updatedMessages);
  };

  // 最终保存
  const handleSaveMessages = async () => {
    if (editableMessages.length === 0) return;
    setIsLoading(true);
    try {
      await apiClient.post(`/profiles/${profileId}/messages`, editableMessages);
      alert('保存成功!');
      setEditableMessages([]);
      setFiles([]);
      setTotalUsage(null);
    } catch (error) {
      console.error("Failed to save messages:", error);
      alert('保存失败: ' + (error.response?.data?.detail || error.message));
    } finally {
      setIsLoading(false);
    }
  };

  if (!currentProfile) return <div>Loading profile...</div>;

  return (
    <div>
      <Link to={`/profile/${profileId}`}>&lt; 返回 Profile 详情</Link>
      <h3>上传截图 for {currentProfile.profile_name}</h3>

      {/* [修改] 使用 className */}
      <div className="uploader">
        <input type="file" multiple onChange={handleFileChange} />
        <button onClick={handleVLMUpload} disabled={isLoading || files.length === 0}>
          {isLoading ? '正在解析...' : `解析 ${files.length} 张图片`}
        </button>
      </div>

      {totalUsage && (
        // [修改] 使用 className
        <div className="token-usage">
          解析完成! 总Token消耗: {totalUsage.total_tokens} (Prompt: {totalUsage.prompt_tokens}, Completion: {totalUsage.completion_tokens})
        </div>
      )}

      <hr />

      <h3>编辑解析结果 (共 {editableMessages.length} 条)</h3>
      {/* [修改] 使用 className */}
      <div className="message-list-editor">
        {editableMessages.map((msg, index) => (
          <EditableMessage
            key={msg.message_id || index}
            message={msg}
            profile={currentProfile}
            onChange={(field, value) => handleMessageChange(index, field, value)}
          />
        ))}
      </div>

      {editableMessages.length > 0 && (
        <button
          onClick={handleSaveMessages}
          disabled={isLoading}
          // [修改] 使用 className
          className="save-button"
        >
          {isLoading ? '保存中...' : '确认并保存所有消息'}
        </button>
      )}
    </div>
  );
}

export default ChatUpload;