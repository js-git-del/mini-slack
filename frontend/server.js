const express = require('express');
const path = require('path');

const app = express();
const PORT = 3000;

// 정적 파일 서빙
app.use(express.static('public'));

// 메인 페이지
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.listen(PORT, () => {
    console.log('='.repeat(50));
    console.log('🚀 Node.js 프론트엔드 서버 시작');
    console.log(`📍 URL: http://localhost:${PORT}`);
    console.log('='.repeat(50));
});