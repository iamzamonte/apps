# simcut

> macOS / Windows 데스크탑 사진 편집 앱

## 주요 기능 (Phase 1 MVP)

- 이미지 불러오기 (`Cmd+O`, 드래그 & 드롭)
- 이미지 내보내기 (`Cmd+Shift+S`) — PNG · JPEG · WebP · BMP
- 사각형 / 원 도형 추가 (선 색상 · 굵기 · 채움색 커스터마이즈)
- Undo (`Cmd+Z`) / Redo (`Cmd+Shift+Z`)

## 기술 스택

| 분류 | 기술 |
|------|------|
| 언어 | Python 3 |
| GUI | PyQt6 |
| 이미지 처리 | Pillow |
| 패키징 | PyInstaller (.app / .exe) |
| 테스트 | pytest · pytest-qt · pytest-cov |

## 빠른 시작

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

## 프로젝트 구조

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

## 개발 로드맵

| Phase | 내용 | 상태 |
|-------|------|------|
| 1 | macOS MVP — 도형, Undo/Redo | ✅ 완료 |
| 2 | 도형 선택/이동, 텍스트, 크롭/리사이즈 | 📅 예정 |
| 3 | Windows 지원 & 패키징 | 📅 예정 |
