from __future__ import annotations

# ── 색상 팔레트 (Light Editor Theme) ────────────────────────────
BG_DARK = "#F5F5F7"           # 앱 배경 (밝은 그레이)
SURFACE = "#FFFFFF"            # 패널, 사이드바 (화이트)
SURFACE_RAISED = "#F0F0F2"     # 호버, 활성 영역
BORDER = "#E0E0E6"             # 구분선, 테두리
ACCENT = "#3B82F6"             # 선택, 포커스 (블루-500)
ACCENT_HOVER = "#2563EB"       # 액센트 호버 (블루-600)
GREEN = "#22C55E"              # 성공, 활성 도구
GREEN_HOVER = "#16A34A"        # 활성 도구 호버
TEXT_PRIMARY = "#1E1E2E"       # 기본 텍스트 (거의 블랙)
TEXT_SECONDARY = "#6B7280"     # 보조 텍스트 (그레이-500)
TEXT_MUTED = "#9CA3AF"         # 비활성 텍스트 (그레이-400)
CANVAS_BG = "#E8E8EC"          # 캔버스 배경 (뉴트럴 그레이)
SCROLLBAR_BG = "#F5F5F7"       # 스크롤바 배경
SCROLLBAR_HANDLE = "#C4C4CC"   # 스크롤바 핸들

# ── 글로벌 스타일시트 ────────────────────────────────────────────
APP_STYLESHEET = f"""
/* ── 기본 위젯 ───────────────────────────────── */
QMainWindow {{
    background-color: {BG_DARK};
}}
QWidget {{
    background-color: {BG_DARK};
    color: {TEXT_PRIMARY};
    font-family: "Helvetica Neue", "Pretendard", sans-serif;
    font-size: 13px;
}}

/* ── 메뉴바 ──────────────────────────────────── */
QMenuBar {{
    background-color: {SURFACE};
    color: {TEXT_PRIMARY};
    border-bottom: 1px solid {BORDER};
    padding: 2px 4px;
    font-size: 13px;
}}
QMenuBar::item {{
    background: transparent;
    padding: 4px 10px;
    border-radius: 4px;
}}
QMenuBar::item:selected {{
    background-color: {SURFACE_RAISED};
}}
QMenu {{
    background-color: {SURFACE};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 24px 6px 12px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background-color: {ACCENT};
    color: white;
}}
QMenu::separator {{
    height: 1px;
    background: {BORDER};
    margin: 4px 8px;
}}

/* ── 상태바 ──────────────────────────────────── */
QStatusBar {{
    background-color: {SURFACE};
    color: {TEXT_SECONDARY};
    border-top: 1px solid {BORDER};
    font-size: 12px;
    padding: 2px 8px;
}}

/* ── 일반 버튼 ───────────────────────────────── */
QPushButton {{
    background-color: {SURFACE};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 5px 12px;
    font-size: 12px;
    min-height: 24px;
}}
QPushButton:hover {{
    background-color: {SURFACE_RAISED};
    border-color: #C8C8D0;
}}
QPushButton:pressed {{
    background-color: {ACCENT};
    color: white;
}}
QPushButton:checked {{
    background-color: {ACCENT};
    color: white;
    border-color: {ACCENT};
}}

/* ── 스핀박스 ────────────────────────────────── */
QSpinBox {{
    background-color: {SURFACE};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 2px 6px;
    min-width: 48px;
    min-height: 24px;
}}
QSpinBox:focus {{
    border-color: {ACCENT};
}}
QSpinBox::up-button, QSpinBox::down-button {{
    background-color: {SURFACE_RAISED};
    border: none;
    width: 16px;
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
    background-color: {BORDER};
}}

/* ── 콤보박스 ────────────────────────────────── */
QComboBox {{
    background-color: {SURFACE};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 4px 8px;
    min-height: 24px;
}}
QComboBox:hover {{
    border-color: {ACCENT};
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox QAbstractItemView {{
    background-color: {SURFACE};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    selection-background-color: {ACCENT};
    selection-color: white;
}}

/* ── 라벨 ────────────────────────────────────── */
QLabel {{
    color: {TEXT_SECONDARY};
    background: transparent;
    font-size: 12px;
}}

/* ── 스크롤 영역 ─────────────────────────────── */
QScrollArea {{
    background-color: {CANVAS_BG};
    border: none;
}}
QScrollBar:vertical {{
    background: {SCROLLBAR_BG};
    width: 10px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: {SCROLLBAR_HANDLE};
    border-radius: 5px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {TEXT_MUTED};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: {SCROLLBAR_BG};
    height: 10px;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background: {SCROLLBAR_HANDLE};
    border-radius: 5px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {TEXT_MUTED};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ── 스플리터 ────────────────────────────────── */
QSplitter::handle {{
    background-color: {BORDER};
    width: 1px;
}}
QSplitter::handle:hover {{
    background-color: {ACCENT};
}}

/* ── 리스트 위젯 (파일 탐색기) ───────────────── */
QListWidget {{
    background-color: {SURFACE};
    color: {TEXT_PRIMARY};
    border: none;
    border-radius: 6px;
    outline: none;
    padding: 4px;
}}
QListWidget::item {{
    background-color: transparent;
    color: {TEXT_PRIMARY};
    border-radius: 6px;
    padding: 6px 4px;
    margin: 2px 0;
}}
QListWidget::item:selected {{
    background-color: {ACCENT};
    color: white;
}}
QListWidget::item:hover:!selected {{
    background-color: {SURFACE_RAISED};
}}

/* ── 다이얼로그 ──────────────────────────────── */
QDialog {{
    background-color: {SURFACE};
}}
QDialogButtonBox QPushButton {{
    min-width: 70px;
}}

/* ── 프레임 (구분선) ─────────────────────────── */
QFrame[frameShape="5"] {{
    color: {BORDER};
    max-width: 1px;
}}

/* ── 프로그레스 다이얼로그 ────────────────────── */
QProgressDialog {{
    background-color: {SURFACE};
}}
QProgressBar {{
    background-color: {SURFACE_RAISED};
    border: 1px solid {BORDER};
    border-radius: 4px;
    text-align: center;
    color: {TEXT_PRIMARY};
    min-height: 18px;
}}
QProgressBar::chunk {{
    background-color: {ACCENT};
    border-radius: 3px;
}}

/* ── 메시지 박스 ─────────────────────────────── */
QMessageBox {{
    background-color: {SURFACE};
}}
QMessageBox QLabel {{
    color: {TEXT_PRIMARY};
    font-size: 13px;
}}
"""

# ── 컴포넌트별 스타일 ────────────────────────────────────────────
TOOLBAR_STYLE = f"""
    background-color: {SURFACE};
    border-bottom: 1px solid {BORDER};
"""

FILE_EXPLORER_STYLE = f"""
    background-color: {BG_DARK};
    border-left: 1px solid {BORDER};
"""

FILE_EXPLORER_TITLE_STYLE = f"""
    font-weight: 600;
    font-size: 11px;
    color: {TEXT_SECONDARY};
    text-transform: uppercase;
    letter-spacing: 1px;
    padding: 8px 4px 4px 4px;
    background: transparent;
"""

TOOL_BTN_FILE_STYLE = f"""
    QPushButton {{
        background-color: transparent;
        color: {TEXT_PRIMARY};
        border: 1px solid transparent;
        border-radius: 6px;
        padding: 4px 10px;
        font-size: 12px;
    }}
    QPushButton:hover {{
        background-color: {SURFACE_RAISED};
        border-color: {BORDER};
    }}
    QPushButton:pressed {{
        background-color: {ACCENT};
        color: white;
    }}
"""

TOOL_BTN_SHAPE_STYLE = f"""
    QPushButton {{
        background-color: transparent;
        color: {TEXT_PRIMARY};
        border: 1px solid transparent;
        border-radius: 6px;
        padding: 4px 10px;
        font-size: 12px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        background-color: {SURFACE_RAISED};
        border-color: {BORDER};
    }}
    QPushButton:checked {{
        background-color: {GREEN};
        color: white;
        border-color: {GREEN};
    }}
    QPushButton:checked:hover {{
        background-color: {GREEN_HOVER};
    }}
"""

COLOR_BTN_STYLE_TEMPLATE = """
    QPushButton {{
        background-color: {bg_color};
        color: white;
        border: 2px solid {border_color};
        border-radius: 6px;
        padding: 4px 10px;
        font-size: 12px;
        min-width: 60px;
    }}
    QPushButton:hover {{
        border-color: {accent};
    }}
"""

FILL_NONE_STYLE = f"""
    QPushButton {{
        background-color: transparent;
        color: {TEXT_SECONDARY};
        border: 2px dashed {BORDER};
        border-radius: 6px;
        padding: 4px 10px;
        font-size: 12px;
        min-width: 60px;
    }}
    QPushButton:hover {{
        border-color: {ACCENT};
        color: {TEXT_PRIMARY};
    }}
"""


def color_btn_stylesheet(color: str) -> str:
    """색상 버튼에 적용할 스타일시트를 생성합니다."""
    return COLOR_BTN_STYLE_TEMPLATE.format(
        bg_color=color,
        border_color=BORDER,
        accent=ACCENT,
    )
