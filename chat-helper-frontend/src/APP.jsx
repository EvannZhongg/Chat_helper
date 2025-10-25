import React from 'react';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import ProfileList from './pages/ProfileList';
import ProfileDetail from './pages/ProfileDetail';
import ChatUpload from './pages/ChatUpload';
import EventUpload from './pages/EventUpload';

function App() {
  return (
    <BrowserRouter>
      {/* .app-container 现在是全屏的、垂直布局的 Flex 容器
        (见 App.css)
      */}
      <div className="app-container">
        {/* 我们把 <header> 移到 .app-container 的直属子级
          并给它一个新类名，使其成为一个全宽的导航栏
        */}
        <header className="app-header">
          <div className="header-content">
            <h1>
              <Link to="/">
                Chat Helper (社交军师)
              </Link>
            </h1>
          </div>
        </header>

        {/* .app-main-content 是新的内容容器
          它会占据剩余空间、内部滚动，并保持内容居中
        */}
        <main className="app-main-content">
          <Routes>
            <Route path="/" element={<ProfileList />} />
            <Route path="/profile/:profileId" element={<ProfileDetail />} />
            <Route path="/profile/:profileId/upload" element={<ChatUpload />} />
            <Route path="/profile/:profileId/events/new" element={<EventUpload />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;