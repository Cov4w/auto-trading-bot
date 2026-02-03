# 🪟 Windows Setup Guide

Windows 환경에서 트레이딩 봇을 설치하고 실행하는 방법입니다.

## 1. 사전 준비 (Prerequisites)

다음 프로그램들이 설치되어 있어야 합니다.

1.  **Python 3.8 이상**: [python.org](https://www.python.org/downloads/)에서 다운로드 (설치 시 "Add Python to PATH" 체크 필수!)
2.  **Node.js**: [nodejs.org](https://nodejs.org/)에서 LTS 버전 다운로드
3.  **Git**: [git-scm.com](https://git-scm.com/)에서 다운로드

---

## 2. 간편 설치 (Automatic Setup)

프로젝트 루트 폴더(`bitThumb_std`)에서 **`setup.bat`** 파일을 더블 클릭하여 실행하세요.

이 스크립트는 다음 작업을 자동으로 수행합니다:
*   Python 가상환경(`venv`) 생성
*   백엔드 라이브러리 설치 (`requirements.txt`)
*   프론트엔드 라이브러리 설치 (`npm install`)
*   `.env` 파일 생성

> **참고:** 실행 중 "Windows PC 보호" 경고가 뜨면 "추가 정보" -> "실행"을 클릭하세요.

---

## 3. 실행 방법 (Running the App)

설치가 완료되면 **`start_dev.bat`** 파일을 더블 클릭하세요.

두 개의 검은색 명령 프롬프트(CMD) 창이 열립니다:
1.  **Backend Server**: FastAPI 서버 (포트 8000)
2.  **Frontend Server**: React 개발 서버 (포트 3000)

브라우저가 자동으로 열리지 않으면 [http://localhost:3000](http://localhost:3000)으로 접속하세요.

---

## 4. 수동 설치 방법 (Manual Setup)

자동 스크립트가 작동하지 않을 경우 터미널(PowerShell 또는 CMD)에서 직접 입력하세요.

### 1단계: Backend 설정
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 2단계: Frontend 설정
```powershell
cd frontend
npm install
cd ..
```

### 3단계: `.env` 설정
`.env.example` 파일을 복사해서 `.env`로 이름을 바꾸고 API 키를 입력하세요.

### 4단계: 실행
터미널 2개를 각각 열어서 실행합니다.

**터미널 1 (Backend):**
```powershell
.\venv\Scripts\activate
cd backend
uvicorn main:app --reload
```

**터미널 2 (Frontend):**
```powershell
cd frontend
npm run dev
```
