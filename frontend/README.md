# Trading Bot Frontend

React + TypeScript + Vite 기반의 트레이딩 봇 대시보드입니다.

## 🚀 기술 스택

- **React 18.2** - UI 프레임워크
- **TypeScript** - 타입 안전성
- **Vite** - 빠른 개발 서버 및 빌드
- **Recharts** - 차트 라이브러리
- **Axios** - HTTP 클라이언트
- **React Router** - 라우팅
- **Lucide React** - 아이콘

## 📦 설치

```bash
npm install
```

## 🏃 개발 모드 실행

```bash
npm run dev
```

Frontend 서버가 http://localhost:3000 에서 실행됩니다.

## 🏗️ 빌드

```bash
npm run build
```

빌드 결과물은 `dist/` 폴더에 생성됩니다.

## 📁 프로젝트 구조

```
frontend/
├── src/
│   ├── pages/
│   │   ├── Dashboard.tsx      # 메인 대시보드
│   │   └── Login.tsx          # 로그인 페이지
│   ├── components/
│   │   ├── ControlPanel.tsx   # 봇 제어 패널
│   │   ├── ModelPerformance.tsx  # AI 성과 차트
│   │   └── TradingSettings.tsx   # 매매 설정
│   ├── contexts/
│   │   └── AuthContext.tsx    # JWT 인증 상태
│   ├── styles/
│   │   └── dashboard.css      # 커스텀 스타일
│   ├── App.tsx               # 라우팅 설정
│   └── main.tsx              # 엔트리 포인트
├── public/
├── package.json
├── vite.config.ts
└── tsconfig.json
```

## 🔑 주요 기능

### 1. JWT 인증
- LocalStorage에 토큰 저장
- 자동 로그인 유지
- 토큰 만료 시 자동 로그아웃

### 2. 실시간 대시보드
- **Balance Section**: 현재 잔고, 총 자산, 수익률
- **Control Panel**: 봇 시작/중지, 재학습, 추천 업데이트
- **Model Performance**: AI 정확도, 승률, 총 거래 수
- **Recommendations**: Top 5 추천 코인 및 스코어

### 3. WebSocket 연동 (예정)
- 실시간 시세 업데이트
- 포지션 변화 알림

## 🔧 환경 변수

프로젝트 루트의 `frontend/.env` 파일에서 설정:

```env
VITE_API_URL=http://localhost:8000
```

## 🎨 스타일링

- **CSS Modules**: 컴포넌트별 스타일 격리
- **반응형 디자인**: 모바일/태블릿/데스크톱 지원
- **Dark Mode Ready**: 다크 모드 대응 준비

## 📚 참고 문서

- [React Documentation](https://react.dev/)
- [Vite Documentation](https://vitejs.dev/)
- [TypeScript Documentation](https://www.typescriptlang.org/)
- [Recharts Documentation](https://recharts.org/)

## 🔗 관련 링크

- [Backend API Documentation](http://localhost:8000/docs)
- [Main README](../README.md)
