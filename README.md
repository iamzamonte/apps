# apps

개인 사이드 프로젝트 모노레포입니다.

## 프로젝트 목록

| 프로젝트 | 설명 | 스택 | 상태 |
|---------|------|------|------|
| [unfollowlens](#unfollowlens) | Instagram 맞팔 분석 웹 앱 | Vanilla JS · Cloudflare Pages · Cloud Run | 🟢 프로덕션 |
| [simcut](#simcut) | 데스크탑 사진 편집 앱 | Python · PyQt6 · Pillow | 🟡 MVP |

---

## unfollowlens

> Instagram에서 나를 팔로우하지 않는 계정을 찾아주는 웹 애플리케이션

**라이브:** https://unfollowlens.com/

### 주요 기능

- Instagram 데이터 ZIP 파일 업로드 후 클라이언트 사이드 분석 (서버 저장 없음)
- 맞팔하지 않는 계정 탐지 및 계정 상태 확인 (활성 / 탈퇴 / 제한 / 비공개)
- 프로필 이미지 프록시 표시
- 다국어 지원: 한국어 · English · 日本語 · 中文 · Español

### 기술 스택

| 분류 | 기술 |
|------|------|
| Frontend | HTML · CSS · JavaScript (Vanilla SPA) |
| Edge Functions | Cloudflare Pages Functions |
| 프록시 서버 | Google Cloud Run (Express · 이중 TLS) |
| 테스트 | Vitest |
| 린트 / 포맷 | ESLint 9 · Prettier |
| 배포 | Cloudflare Pages + Cloud Build |

### 아키텍처

```
사용자 브라우저
├── dist/index.html           # SPA (ZIP 파싱, 비교, 렌더링)
│
├── /api/check-account        # Cloudflare Function
│   └── Instagram 계정 상태 확인 (og:* 메타태그 파싱)
│       └── 429 시 Cloud Run 프록시로 폴백
│
└── /api/proxy-image          # Cloudflare Function
    └── Instagram CDN 이미지 프록시 (허용 호스트 검증, 5MB 제한)
```

### 빠른 시작

```bash
cd unfollowlens
npm install

# 로컬 개발 서버 (http://localhost:8788)
npm run dev

# 테스트
npm test

# 린트 + 포맷 + 테스트 (CI 전체)
npm run ci
```

### Instagram 데이터 다운로드 방법

1. Instagram **설정** → **계정 센터** → **내 정보 및 권한**
2. **내 정보 다운로드** → **일부 정보 다운로드** → **팔로워 및 팔로잉**
3. 형식: **JSON** · 기간: **전체 기간**
4. 이메일로 받은 ZIP 파일을 앱에 업로드

### 프로젝트 구조

```
unfollowlens/
├── dist/                       # 빌드된 SPA
│   └── index.html
├── functions/api/
│   ├── check-account.js        # 계정 상태 확인 API
│   ├── proxy-image.js          # 이미지 프록시 API
│   └── _middleware.js
├── cloud-run/                  # GCP Cloud Run 프록시 서버
│   ├── index.js
│   └── Dockerfile
├── tests/                      # Vitest 단위 테스트
├── docs/                       # PRD, SEO 가이드, 모니터링 가이드
├── wrangler.jsonc
└── package.json
```

---

## simcut

> macOS / Windows 데스크탑 사진 편집 앱

### 주요 기능 (Phase 1 MVP)

- 이미지 불러오기 (`Cmd+O`, 드래그 & 드롭)
- 이미지 내보내기 (`Cmd+Shift+S`) — PNG · JPEG · WebP · BMP
- 사각형 / 원 도형 추가 (선 색상 · 굵기 · 채움색 커스터마이즈)
- Undo (`Cmd+Z`) / Redo (`Cmd+Shift+Z`)

### 기술 스택

| 분류 | 기술 |
|------|------|
| 언어 | Python 3 |
| GUI | PyQt6 |
| 이미지 처리 | Pillow |
| 패키징 | PyInstaller (.app / .exe) |
| 테스트 | pytest · pytest-qt · pytest-cov |

### 빠른 시작

```bash
cd simcut

# 가상환경 설정
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 실행
python -m src.main

# 테스트
pytest tests/ -v --cov=src --cov-report=term-missing
```

### 프로젝트 구조

```
simcut/
├── src/
│   ├── main.py                 # 앱 진입점
│   ├── ui/
│   │   ├── main_window.py      # 메인 윈도우 & 레이아웃
│   │   ├── canvas.py           # 이미지 편집 캔버스
│   │   ├── toolbar.py          # 도구 모음
│   │   └── properties.py       # 속성 패널
│   ├── core/
│   │   ├── image_handler.py    # 이미지 I/O & 변환
│   │   └── shape_manager.py    # 도형 관리 & Undo/Redo
│   └── utils/
│       ├── constants.py        # 앱 상수
│       └── theme.py            # 다크 / 라이트 테마
├── tests/                      # pytest 단위 · 통합 테스트
├── docs/plans/                 # 설계 & 구현 계획 문서
├── simcut.spec                 # PyInstaller 패키징 설정
└── requirements.txt
```

### 개발 로드맵

| Phase | 내용 | 상태 |
|-------|------|------|
| 1 | macOS MVP — 도형, Undo/Redo | ✅ 완료 |
| 2 | 도형 선택/이동, 텍스트, 크롭/리사이즈 | 📅 예정 |
| 3 | Windows 지원 & 패키징 | 📅 예정 |

---

## 라이선스

MIT License
