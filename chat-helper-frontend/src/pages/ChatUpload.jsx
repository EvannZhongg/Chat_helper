import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useProfileStore } from '../store/profileStore';
import apiClient from '../api/apiClient';
import EditableMessage from '../components/EditableMessage';
import { v4 as uuidv4 } from 'uuid';

// ... (fileToDataUrl 和 UploadProgress 组件保持不变) ...
const fileToDataUrl = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
};
function UploadProgress({ progress }) {
  if (!progress.total) return null;
  const percent = Math.round((progress.current / progress.total) * 100);
  return (
    <div className="upload-progress-container">
      <label>正在解析: {progress.current} / {progress.total} ( {percent}% )</label>
      <progress value={progress.current} max={progress.total}></progress>
    </div>
  );
}


function ChatUpload() {
  const { profileId } = useParams();
  const { currentProfile, getProfile } = useProfileStore();

  const [files, setFiles] = useState([]);
  const [editableMessages, setEditableMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [totalUsage, setTotalUsage] = useState({ prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 });

  const [imagePreviewMap, setImagePreviewMap] = useState({});
  const [progress, setProgress] = useState({ current: 0, total: 0 });

  useEffect(() => {
    if (profileId) {
      getProfile(profileId);
    }
  }, [profileId, getProfile]);

  const handleFileChange = (e) => {
    // ... (此函数保持不变) ...
    const newFiles = Array.from(e.target.files);
    setFiles(newFiles);
    if (newFiles.length > 0) {
      setEditableMessages([]);
      setTotalUsage({ prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 });
      setImagePreviewMap({});
      setProgress({ current: 0, total: 0 });
    }
  };

  const handleVLMUpload = async () => {
    // ... (此函数保持不变) ...
    if (files.length === 0) return;
    setIsLoading(true);
    setProgress({ current: 0, total: files.length });
    let fileDataUrls = [];
    try {
      fileDataUrls = await Promise.all(files.map(fileToDataUrl));
    } catch (readError) {
      console.error("File read failed:", readError);
      alert("读取图片文件失败");
      setIsLoading(false);
      return;
    }
    let currentRunMessages = [];
    const currentRunImageMap = {};
    const currentRunUsage = { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 };
    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        setProgress({ current: i + 1, total: files.length });
        const formData = new FormData();
        formData.append('files', file);
        const response = await apiClient.post(
          `/import/${profileId}/upload_screenshots`,
          formData,
          { headers: { 'Content-Type': 'multipart/form-data' } }
        );
        const { results, total_usage } = response.data;
        if (results && results.length > 0) {
          const result = results[0];
          const imageHash = result.image_hash;
          const dataUrl = fileDataUrls[i];
          if (imageHash && dataUrl) {
            currentRunImageMap[imageHash] = dataUrl;
          }
          const messagesWithHash = result.messages.map(msg => ({
            ...msg,
            source_image_hash: imageHash
          }));
          currentRunMessages.push(...messagesWithHash);
        }
        if (total_usage) {
          currentRunUsage.prompt_tokens += total_usage.prompt_tokens;
          currentRunUsage.completion_tokens += total_usage.completion_tokens;
          currentRunUsage.total_tokens += total_usage.total_tokens;
        }
        const sortedMessages = [...currentRunMessages].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
        setEditableMessages(sortedMessages);
        setImagePreviewMap({...currentRunImageMap});
        setTotalUsage({...currentRunUsage});
      }
    } catch (error) {
      console.error("VLM upload failed:", error);
      alert("解析失败: " + (error.response?.data?.detail || error.message));
    } finally {
      setIsLoading(false);
      setProgress({ current: 0, total: 0 });
      setFiles([]);
      const fileInput = document.getElementById('chat-file-input');
      if (fileInput) {
        fileInput.value = "";
      }
    }
  };

  const handleMessageChange = (index, field, value) => {
    // ... (此函数保持不变) ...
    const updatedMessages = [...editableMessages];
    if (field === 'timestamp') {
      updatedMessages[index] = {
        ...updatedMessages[index],
        [field]: value,
        auto_filled_date: false,
        auto_filled_time: false
      };
    } else {
      updatedMessages[index] = { ...updatedMessages[index], [field]: value };
    }
    setEditableMessages(updatedMessages);
  };

  const handleSaveMessages = async () => {
    // ... (此函数保持不变) ...
    if (editableMessages.length === 0) return;
    setIsLoading(true);
    try {
      await apiClient.post(`/profiles/${profileId}/messages`, editableMessages);
      alert('保存成功!');
      setEditableMessages([]);
      setFiles([]);
      setTotalUsage({ prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 });
      setImagePreviewMap({});
      const fileInput = document.getElementById('chat-file-input');
      if (fileInput) {
        fileInput.value = "";
      }
    } catch (error) {
      console.error("Failed to save messages:", error);
      alert('保存失败: ' + (error.response?.data?.detail || error.message));
    } finally {
      setIsLoading(false);
    }
  };

  const handleInsertTemplate = (hash) => {
    // ... (此函数保持不变) ...
    let latestTimestamp = null;
    const relevantMessages = editableMessages.filter(m => m.source_image_hash === hash);
    if (relevantMessages.length > 0) {
      latestTimestamp = relevantMessages[relevantMessages.length - 1].timestamp;
    }
    const newTimestamp = latestTimestamp
      ? new Date(new Date(latestTimestamp).getTime() + 1000)
      : new Date();
    const newTemplate = {
      message_id: `msg_${uuidv4()}`,
      timestamp: newTimestamp.toISOString(),
      sender: 'User 1',
      content_type: 'text',
      text: '',
      media_description: null,
      source_image_hash: hash,
      is_editable: true,
      raw_vlm_output: 'Manual template',
      auto_filled_date: true,
      auto_filled_time: true
    };
    let insertionIndex = editableMessages.length; // 默认在末尾
    if (latestTimestamp) {
      // 找到最后一条相关消息的索引
      const lastMsgIndex = editableMessages.findIndex(m => m.timestamp === latestTimestamp);
      if (lastMsgIndex > -1) {
        insertionIndex = lastMsgIndex + 1; // 在它后面插入
      }
    }

    // 在计算出的索引处插入新模板
    const newMessages = [...editableMessages];
    newMessages.splice(insertionIndex, 0, newTemplate);
    setEditableMessages(newMessages);
  };

  const handleMoveMessage = (globalIndex, direction) => {
    const newMessages = [...editableMessages];
    const i = globalIndex;
    const j = (direction === 'up') ? i - 1 : i + 1;

    // 检查是否越界
    if (j < 0 || j >= newMessages.length) {
      return;
    }

    // 检查是否跨组 (此逻辑保持不变，保证组内排序)
    if (newMessages[i].source_image_hash !== newMessages[j].source_image_hash) {
      alert("不能将消息移动到不同的图片组。");
      return;
    }

    // [核心]
    // 我们不再只是交换位置，而是交换时间戳
    // 这样，当后端按时间戳排序时，会尊重我们的新顺序。

    const time_i = new Date(newMessages[i].timestamp);
    const time_j = new Date(newMessages[j].timestamp);

    let new_time_i, new_time_j;

    if (direction === 'up') {
      // 消息 'i' 要移动到 'j' (i-1) 的位置，它需要一个更早的时间
      if (time_i >= time_j) {
        // 如果 'i' 的时间晚于或等于 'j'
        // 我们把 'i' 的时间设为 'j' 之前 1 毫秒
        // 'j' 的时间保持不变
        new_time_i = new Date(time_j.getTime() - 1);
        new_time_j = time_j;
      } else {
        // 如果 'i' 的时间已早于 'j' (例如 10:00 vs 10:01)
        // 我们直接交换它们的时间
        new_time_i = time_j;
        new_time_j = time_i;
      }
    } else { // direction === 'down'
      // 消息 'i' 要移动到 'j' (i+1) 的位置，它需要一个更晚的时间
      if (time_i <= time_j) {
        // 如果 'i' 的时间早于或等于 'j'
        // 我们把 'i' 的时间设为 'j' 之后 1 毫秒
        // 'j' 的时间保持不变
        new_time_i = new Date(time_j.getTime() + 1);
        new_time_j = time_j;
      } else {
        // 如果 'i' 的时间已晚于 'j' (例如 10:01 vs 10:00)
        // 我们直接交换它们的时间
        new_time_i = time_j;
        new_time_j = time_i;
      }
    }

    // 更新消息对象的时间戳
    newMessages[i] = {
      ...newMessages[i],
      timestamp: new_time_i.toISOString(),
      auto_filled_date: true, // 标记为红色，提示用户已修改
      auto_filled_time: true
    };
    newMessages[j] = {
      ...newMessages[j],
      timestamp: new_time_j.toISOString(),
      // 只有被交换的那个需要标红
      auto_filled_date: (new_time_j !== time_j) ? true : newMessages[j].auto_filled_date,
      auto_filled_time: (new_time_j !== time_j) ? true : newMessages[j].auto_filled_time,
    };

    // [修改]
    // 我们不再需要交换它们在数组中的位置，
    // 而是对整个列表按*新*的时间戳重新排序，以刷新UI
    newMessages.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

    setEditableMessages(newMessages);
  };

  // [新增] 删除消息的逻辑
  const handleDeleteMessage = (globalIndex) => {
    if (!window.confirm("确定要删除这条记录吗？")) {
      return;
    }
    const newMessages = [...editableMessages];
    newMessages.splice(globalIndex, 1); // 从数组中移除
    setEditableMessages(newMessages);
  };


  const getRenderGroups = () => {
    // ... (此函数保持不变) ...
    const renderGroups = [];
    const manualEntries = [];
    const hashToGroupIndex = {};
    editableMessages.forEach((msg) => {
      const hash = msg.source_image_hash || 'manual_entry';
      if (hash === 'manual_entry') {
        manualEntries.push(msg);
        return;
      }
      if (hashToGroupIndex[hash] === undefined) {
        hashToGroupIndex[hash] = renderGroups.length;
        renderGroups.push({
          hash: hash,
          previewUrl: imagePreviewMap[hash],
          messages: [msg]
        });
      } else {
        const groupIndex = hashToGroupIndex[hash];
        renderGroups[groupIndex].messages.push(msg);
      }
    });
    return { renderGroups, manualEntries };
  };

  const getGlobalIndex = (message_id) => {
    return editableMessages.findIndex(m => m.message_id === message_id);
  }

  if (!currentProfile) return <div>Loading profile...</div>;

  const { renderGroups, manualEntries } = getRenderGroups();

  return (
    <div>
      <Link to={`/profile/${profileId}`}>&lt; 返回 Profile 详情</Link>
      <h3>上传截图 for {currentProfile.profile_name}</h3>

      {/* ... (uploader, progress, token usage, hr, h3 保持不变) ... */}
      <div className="uploader">
        <input
          id="chat-file-input"
          type="file"
          multiple
          onChange={handleFileChange}
        />
        <button onClick={handleVLMUpload} disabled={isLoading || files.length === 0}>
          {isLoading ? '正在解析...' : `解析 ${files.length} 张图片`}
        </button>
      </div>
      {isLoading && <UploadProgress progress={progress} />}
      {!isLoading && totalUsage.total_tokens > 0 && (
        <div className="token-usage">
          解析完成! 总Token消耗: {totalUsage.total_tokens} (Prompt: {totalUsage.prompt_tokens}, Completion: {totalUsage.completion_tokens})
        </div>
      )}
      <hr />
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3>编辑解析结果 (共 {editableMessages.length} 条)</h3>
        <button
          onClick={() => handleInsertTemplate('manual_entry')}
          className="insert-manual-btn"
        >
          + 插入手动消息
        </button>
      </div>

      <div className="message-list-editor">
        {/* 1. 渲染图片组 */}
        {renderGroups.map(group => (
          <div key={group.hash} className="image-message-group">
            <div className="image-preview-container">
              {group.previewUrl && <img src={group.previewUrl} alt={`Source ${group.hash.substring(0, 6)}`} />}
            </div>
            <div className="messages-container">
              {/* [修改] 传递 onDelete 和 修复 isFirst/Last */}
              {group.messages.map((msg, indexInGroup) => {
                const globalIndex = getGlobalIndex(msg.message_id);
                if (globalIndex === -1) return null;
                return (
                  <EditableMessage
                    key={msg.message_id}
                    message={msg}
                    profile={currentProfile}
                    onChange={(field, value) => handleMessageChange(globalIndex, field, value)}
                    onMove={(direction) => handleMoveMessage(globalIndex, direction)}
                    onDelete={() => handleDeleteMessage(globalIndex)}
                    isFirstInGroup={indexInGroup === 0}
                    isLastInGroup={indexInGroup === group.messages.length - 1}
                  />
                );
              })}
              <div className="add-message-to-group">
                <button
                  className="add-message-to-group-btn"
                  onClick={() => handleInsertTemplate(group.hash)}
                >
                  + 插入消息到此组
                </button>
              </div>
            </div>
          </div>
        ))}

        {/* 2. 渲染手动组 */}
        {manualEntries.length > 0 && (
          <div className="image-message-group manual-group">
            <div className="image-preview-container">
               <div className="manual-entry-placeholder">手动添加</div>
            </div>
            <div className="messages-container">
              {/* [修改] 传递 onDelete 和 修复 isFirst/Last */}
              {manualEntries.map((msg, indexInGroup) => {
                const globalIndex = getGlobalIndex(msg.message_id);
                if (globalIndex === -1) return null;
                return (
                  <EditableMessage
                    key={msg.message_id}
                    message={msg}
                    profile={currentProfile}
                    onChange={(field, value) => handleMessageChange(globalIndex, field, value)}
                    onMove={(direction) => handleMoveMessage(globalIndex, direction)}
                    onDelete={() => handleDeleteMessage(globalIndex)}
                    isFirstInGroup={indexInGroup === 0}
                    isLastInGroup={indexInGroup === manualEntries.length - 1}
                  />
                );
              })}
              <div className="add-message-to-group">
                 <button
                  className="add-message-to-group-btn"
                  onClick={() => handleInsertTemplate('manual_entry')}
                >
                  + 插入消息到此组
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {editableMessages.length > 0 && (
        <button
          onClick={handleSaveMessages}
          disabled={isLoading}
          className="save-button"
        >
          {isLoading ? '保存中...' : '确认并保存所有消息'}
        </button>
      )}
    </div>
  );
}

export default ChatUpload;