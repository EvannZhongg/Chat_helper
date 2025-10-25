import React, { useState } from 'react';

function ProfileForm({
  onSubmit,
  initialData = { profile_name: '', user_name: '我', opponent_name: '' },
  submitText = '创建'
}) {
  const [formData, setFormData] = useState(initialData);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!formData.profile_name || !formData.opponent_name) {
      alert('Profile 名称和对方名称不能为空');
      return;
    }
    // 注意：这里的 onSubmit 现在是一个 async 函数 (在 ProfileList.jsx 中定义)
    onSubmit(formData);
  };

  // [修改] 替换 style 为 className
  return (
    <form onSubmit={handleSubmit} className="profile-form">
      <div className="form-group">
        <label>档案名称 (e.g., "Boss", "客户A"): </label>
        <input
          type="text"
          name="profile_name"
          value={formData.profile_name}
          onChange={handleChange}
        />
      </div>
      <div className="form-group">
        <label>"我" 的名称: </label>
        <input
          type="text"
          name="user_name"
          value={formData.user_name}
          onChange={handleChange}
        />
      </div>
      <div className="form-group">
        <label>"对方" 的名称: </label>
        <input
          type="text"
          name="opponent_name"
          value={formData.opponent_name}
          onChange={handleChange}
        />
      </div>
      <button type="submit">{submitText}</button>
    </form>
  );
}

export default ProfileForm;