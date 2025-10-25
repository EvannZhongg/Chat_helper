import React from 'react';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import ProfileList from './pages/ProfileList';
import ProfileDetail from './pages/ProfileDetail';
import ChatUpload from './pages/ChatUpload';

function APP() {
  return (
    <BrowserRouter>
      {/* 替换 style 为 className */}
      <div className="app-container">
        <header>
          <h1>
            <Link to="/">
              Chat Helper (社交军师)
            </Link>
          </h1>
        </header>
        <main>
          <Routes>
            <Route path="/" element={<ProfileList />} />
            <Route path="/profile/:profileId" element={<ProfileDetail />} />
            <Route path="/profile/:profileId/upload" element={<ChatUpload />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default APP;