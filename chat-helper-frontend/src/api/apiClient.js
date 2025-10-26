import axios from 'axios';

const apiClient = axios.create({
  baseURL: 'http://127.0.0.1:8003', // 你的FastAPI后端地址
  headers: {
    'Content-Type': 'application/json',
  },
});

export default apiClient;