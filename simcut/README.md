# simcut

간단한 사진 편집 데스크탑 앱 (Mac OS / Windows)

## 주요 기능 (Phase 1 MVP)

- 이미지 불러오기 (`Cmd+O`, 드래그 & 드롭)
- 이미지 내보내기 (`Cmd+Shift+S`) — PNG / JPEG / WebP / BMP
- 사각형 / 원 도형 추가 (선 색상, 선 굵기, 배경 채움색)
- Undo (`Cmd+Z`) / Redo (`Cmd+Shift+Z`)

## 개발 환경 세팅

```bash
cd /Users/montecarlo/Downloads/2_AREA/apps/simcut
python3 -m venv .venv
source .venv/bin/activate          # Mac
# .venv\Scripts\activate           # Windows
pip install -r requirements.txt
```

## 실행

```bash
source .venv/bin/activate
python -m src.main
```

## 테스트

```bash
pytest tests/ -v --cov=src --cov-report=term-missing
```

## 프로젝트 구조

```
simcut/
├── src/
│   ├── main.py               # 앱 진입점
│   ├── ui/
│   │   ├── main_window.py    # 메인 윈도우 & 레이아웃
│   │   ├── canvas.py         # 이미지 편집 캔버스
│   │   ├── toolbar.py        # 도구 모음
│   │   └── properties.py     # 속성 패널
│   ├── core/
│   │   ├── image_handler.py  # 이미지 불러오기 / 저장 / 변환
│   │   └── shape_manager.py  # 도형 & Undo/Redo 관리
│   └── utils/
│       └── constants.py      # 앱 상수
├── tests/                    # 단위 테스트
├── docs/plans/               # 설계 & 구현 계획 문서
└── requirements.txt
```

## 개발 로드맵

| Phase | 내용 | 상태 |
|-------|------|------|
| 1 | Mac OS MVP (현재) | ✅ |
| 2 | 도형 선택/이동, 텍스트, 크롭/리사이즈 | 예정 |
| 3 | Windows 지원 & 패키징 | 예정 |
