// src/APP.jsx

import React from 'react';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import ProfileList from './pages/ProfileList';
import ProfileDetail from './pages/ProfileDetail';
import ChatUpload from './pages/ChatUpload';
import EventUpload from './pages/EventUpload';
import AnalysisPage from './pages/AnalysisPage';
import AssistPage from './pages/AssistPage';
// [!!] 修复：将导入名称改为 TimelineGraphPage 以匹配路由用法
import TimelineGraphPage from './pages/TimelineGraphPage'; // [!!] 修改此行

function App() {
  return (
    <BrowserRouter>
      {/* ... (header and app-container) ... */}
       <header className="app-header">
         <div className="header-content">
           <h1>
             <Link to="/">
               Chat Helper (社交军师)
             </Link>
           </h1>
         </div>
       </header>

       <main className="app-main-content">
         <Routes>
           <Route path="/" element={<ProfileList />} />
           <Route path="/profile/:profileId" element={<ProfileDetail />} />
           <Route path="/profile/:profileId/upload" element={<ChatUpload />} />
           <Route path="/profile/:profileId/events/new" element={<EventUpload />} />
           <Route path="/profile/:profileId/analyze" element={<AnalysisPage />} />
           <Route path="/profile/:profileId/assist" element={<AssistPage />} />
           {/* 路由中的名称保持不变 */}
           <Route path="/profile/:profileId/timeline" element={<TimelineGraphPage />} />
         </Routes>
       </main>
      {/* ... */}
    </BrowserRouter>
  );
}

export default App;