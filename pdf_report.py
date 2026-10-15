"""
pdf_report.py
EASY PASS Executive Report
การทางพิเศษแห่งประเทศไทย (กทพ.)

เวอร์ชันปรับปรุง:
- ใช้ fpdf2
- ใช้ Matplotlib Agg backend
- ไม่ import matplotlib.font_manager
- หลีกเลี่ยง macOS KeyError: '_items'
- รองรับภาษาไทยใน PDF
- รองรับการสร้างกราฟจาก DataFrame
"""

# ============================================================================
# IMPORTS
# ============================================================================

import os
import tempfile
import platform
from pathlib import Path
from datetime import datetime

from fpdf import FPDF

# ---------------------------------------------------------------------------
# Matplotlib
# ---------------------------------------------------------------------------
# สำคัญ:
# ห้าม import matplotlib.font_manager
# เพราะบน macOS บาง environment จะเกิด:
# KeyError: '_items'
# ---------------------------------------------------------------------------

import matplotlib

matplotlib.use("Agg")   # ต้องเรียกก่อน import pyplot

import matplotlib.pyplot as plt


# ============================================================================
# GLOBAL SETTINGS
# ============================================================================

_THAI_FONT_PATH = None

PAGE_WIDTH = 210
PAGE_HEIGHT = 297

MARGIN_LEFT = 12
MARGIN_RIGHT = 12

CONTENT_WIDTH = 186


# ============================================================================
# FONT DETECTION
# ============================================================================

def _detect_thai_font():
    """
    ค้นหาไฟล์ฟอนต์ไทย
    ลำดับ: bundled → ฟอนต์ .ttf ของ OS → ฟอนต์ .ttc
    (ให้ความสำคัญกับ .ttf เพราะ matplotlib จัดการง่ายกว่า .ttc)
    """
    global _THAI_FONT_PATH

    if _THAI_FONT_PATH is not None:
        return _THAI_FONT_PATH or None

    # ---------- 1) bundled ----------
    try:
        base = Path(__file__).parent
        for p in [
            base / "assets" / "fonts" / "NotoSansThai-Regular.ttf",
            base / "assets" / "fonts" / "Sarabun-Regular.ttf",
        ]:
            if p.exists():
                _THAI_FONT_PATH = str(p)
                return _THAI_FONT_PATH
    except Exception:
        pass

    # ---------- 2) OS fonts ----------
    system = platform.system()

    if system == "Darwin":
        candidates = [
            # .ttf ที่ปลอดภัยสุดบน Mac
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
            "/Library/Fonts/Arial Unicode.ttf",
            "/System/Library/Fonts/Supplemental/Tahoma.ttf",
            "/System/Library/Fonts/Supplemental/Tahoma Bold.ttf",
            # ฟอนต์ไทยของ user (ถ้ามี)
            str(Path.home() / "Library/Fonts/THSarabunIT๙.ttf"),
            str(Path.home() / "Library/Fonts/Sarabun-Regular.ttf"),
            # .ttc ทีหลัง (ถ้าไม่มี .ttf)
            "/System/Library/Fonts/Supplemental/Thonburi.ttc",
            "/System/Library/Fonts/ThonburiUI.ttc",
            "/System/Library/AssetsV2/com_apple_MobileAsset_Font8/"
            "cf0dc8d3b09f9ba379660e591e82566e2b557949.asset/AssetData/Sarabun.ttc",
        ]
    elif system == "Windows":
        candidates = [
            "C:/Windows/Fonts/tahoma.ttf",
            "C:/Windows/Fonts/leelawui.ttf",
            "C:/Windows/Fonts/LeelawUI.ttf",
        ]
    else:  # Linux / Docker
        candidates = [
            "/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansThai-Regular.otf",
            "/usr/share/fonts/truetype/tlwg/Garuda.ttf",
            "/usr/share/fonts/truetype/tlwg/Loma.ttf",
            "/usr/share/fonts/truetype/tlwg/Norasi.ttf",
        ]

    for path in candidates:
        if Path(path).exists():
            _THAI_FONT_PATH = path
            return path

    _THAI_FONT_PATH = ""
    return None


# ============================================================================
# MATPLOTLIB CONFIGURATION
# ============================================================================

def _configure_matplotlib():
    """
    ตั้งค่า matplotlib ให้ใช้ฟอนต์ไทย

    จำเป็นต้องใช้ font_manager.addfont() ลงทะเบียน TTF ภายนอก
    เพราะ matplotlib ไม่รู้จักฟอนต์ system ที่ไม่อยู่ใน cache
    """
    plt.rcParams["axes.unicode_minus"] = False

    thai_font = _detect_thai_font()

    if not thai_font:
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans"]
        print("[pdf_report] ⚠️ ไม่พบฟอนต์ไทย — กราฟจะแสดงเป็น ☐")
        return

    try:
        from matplotlib import font_manager

        # ลงทะเบียนฟอนต์
        font_manager.fontManager.addfont(thai_font)

        # ดึงชื่อ family (เช่น "Arial Unicode MS", "Tahoma")
        prop = font_manager.FontProperties(fname=thai_font)
        thai_family = prop.get_name()

        # ตั้งค่า
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = [thai_family, "DejaVu Sans"]

        # บางครั้ง macOS cache เก่าค้าง — บังคับอีกครั้ง
        try:
            matplotlib.rcParams["font.sans-serif"] = [thai_family, "DejaVu Sans"]
        except Exception:
            pass

        print(f"[pdf_report] ✅ ใช้ฟอนต์ไทย: {thai_family}")
        print(f"[pdf_report]    path: {thai_font}")

    except Exception as e:
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans"]
        print(f"[pdf_report] ⚠️ โหลดฟอนต์ไทยไม่สำเร็จ: {type(e).__name__}: {e}")


_configure_matplotlib()

# ============================================================================
# SAFE HELPERS
# ============================================================================

def _safe_float(value, default=0.0):

    try:

        if value is None:
            return default

        if hasattr(value, "item"):
            value = value.item()

        return float(value)

    except Exception:

        return default


def _safe_int(value, default=0):

    try:

        if value is None:
            return default

        if hasattr(value, "item"):
            value = value.item()

        return int(float(value))

    except Exception:

        return default


def _safe_last(df, column, default=0):

    try:

        if df is None:
            return default

        if column not in df.columns:
            return default

        if len(df) == 0:
            return default

        return df[column].iloc[-1]

    except Exception:

        return default


def _safe_previous(df, column, default=0):

    try:

        if df is None:
            return default

        if column not in df.columns:
            return default

        if len(df) < 2:
            return default

        return df[column].iloc[-2]

    except Exception:

        return default


def _pct_change(current, previous):

    current = _safe_float(current)
    previous = _safe_float(previous)

    if previous == 0:
        return 0.0

    return (current - previous) / previous * 100


def _delta(current, previous):

    return _safe_float(current) - _safe_float(previous)


def _fmt_number(value, decimals=0):

    try:

        value = float(value)

        return f"{value:,.{decimals}f}"

    except Exception:

        return "-"


def _fmt_percent(value, decimals=2):

    try:

        return f"{float(value):.{decimals}f}%"

    except Exception:

        return "-"


def _fmt_baht(value):

    try:

        return f"{float(value):,.0f}"

    except Exception:

        return "-"


# ============================================================================
# PDF CLASS
# ============================================================================

class ExecutivePDF(FPDF):

    def __init__(self, latest_month, username):

        super().__init__(
            orientation="P",
            unit="mm",
            format="A4"
        )

        self.latest_month = latest_month
        self.username = username

        self.font_path = _detect_thai_font()

        self.font_name = "Helvetica"

        # -------------------------------------------------------------------
        # Thai Font
        # -------------------------------------------------------------------

        if self.font_path:

            try:

                # Regular
                self.add_font(
                    "Thai",
                    "",
                    self.font_path
                )

                # ใช้ font เดียวกันสำหรับ B/I
                # เพื่อป้องกันปัญหาฟอนต์ไม่ครบ
                try:
                    self.add_font(
                        "Thai",
                        "B",
                        self.font_path
                    )
                except Exception:
                    pass

                try:
                    self.add_font(
                        "Thai",
                        "I",
                        self.font_path
                    )
                except Exception:
                    pass

                self.font_name = "Thai"

            except Exception:

                self.font_name = "Helvetica"

        self.set_auto_page_break(
            auto=True,
            margin=18
        )

        self.set_margins(
            MARGIN_LEFT,
            12,
            MARGIN_RIGHT
        )

        self.alias_nb_pages()


    # ========================================================================
    # HEADER
    # ========================================================================

    def header(self):

        if self.page_no() == 1:
            return

        self.set_fill_color(
            0,
            51,
            102
        )

        self.rect(
            0,
            0,
            PAGE_WIDTH,
            11,
            "F"
        )

        self.set_xy(
            12,
            2.5
        )

        self.set_font(
            self.font_name,
            "B",
            9
        )

        self.set_text_color(
            255,
            255,
            255
        )

        self.cell(
            105,
            6,
            "EASY PASS Executive Report",
            0,
            0,
            "L"
        )

        self.set_font(
            self.font_name,
            "",
            8
        )

        self.set_text_color(
            200,
            220,
            245
        )

        self.cell(
            0,
            6,
            f"การทางพิเศษแห่งประเทศไทย (กทพ.) | {self.latest_month}",
            0,
            1,
            "R"
        )

        self.ln(2)


    # ========================================================================
    # FOOTER
    # ========================================================================

    def footer(self):

        self.set_y(-12)

        self.set_font(
            self.font_name,
            "",
            7
        )

        self.set_text_color(
            140,
            140,
            140
        )

        self.set_draw_color(
            210,
            210,
            210
        )

        self.line(
            12,
            285,
            198,
            285
        )

        self.cell(
            0,
            6,
            f"รายงานลับเพื่อการตัดสินใจของผู้บริหาร | "
            f"ผู้ใช้: {self.username} | "
            f"หน้า {self.page_no()} / {{nb}}",
            0,
            0,
            "C"
        )


    # ========================================================================
    # SECTION TITLE
    # ========================================================================

    def section_title(
        self,
        num,
        text,
        color=(0, 51, 102)
    ):

        if self.get_y() > 255:
            self.add_page()

        self.set_fill_color(*color)

        self.set_text_color(
            255,
            255,
            255
        )

        self.set_font(
            self.font_name,
            "B",
            11
        )

        self.cell(
            0,
            8,
            f"  {num}  {text}",
            0,
            1,
            "L",
            fill=True
        )

        self.set_text_color(
            40,
            40,
            40
        )

        self.ln(2)


    # ========================================================================
    # SUB TITLE
    # ========================================================================

    def sub_title(self, text):

        self.set_font(
            self.font_name,
            "B",
            9.5
        )

        self.set_text_color(
            0,
            80,
            160
        )

        self.cell(
            0,
            6,
            str(text),
            0,
            1,
            "L"
        )

        self.set_text_color(
            40,
            40,
            40
        )

        self.ln(0.5)


    # ========================================================================
    # NOTE
    # ========================================================================

    def note(
        self,
        text,
        color=(120, 120, 120)
    ):

        self.set_font(
            self.font_name,
            "I",
            7.5
        )

        self.set_text_color(*color)

        self.multi_cell(
            0,
            4.5,
            str(text)
        )

        self.set_text_color(
            40,
            40,
            40
        )


    # ========================================================================
    # KPI ROW
    # ========================================================================

    def kpi_row(
        self,
        items,
        per_row=4,
        card_h=18
    ):

        if not items:
            return

        w = (
            CONTENT_WIDTH -
            2 * (per_row - 1)
        ) / per_row

        x0 = self.get_x()
        y0 = self.get_y()

        for i, item in enumerate(items):

            col = i % per_row
            row = i // per_row

            x = x0 + col * (w + 2)
            y = y0 + row * (card_h + 3)

            self._kpi_card(
                x,
                y,
                w,
                card_h,
                item.get("label", ""),
                item.get("value", ""),
                item.get("delta", "")
            )

        rows = (
            len(items) +
            per_row -
            1
        ) // per_row

        self.set_y(
            y0 +
            rows * (card_h + 3) +
            2
        )


    # ========================================================================
    # KPI CARD
    # ========================================================================

    def _kpi_card(
        self,
        x,
        y,
        w,
        h,
        label,
        value,
        delta=""
    ):

        self.set_fill_color(
            245,
            248,
            255
        )

        self.set_draw_color(
            200,
            215,
            240
        )

        self.rect(
            x,
            y,
            w,
            h,
            "DF"
        )

        self.set_xy(
            x + 2,
            y + 1.5
        )

        self.set_font(
            self.font_name,
            "",
            7
        )

        self.set_text_color(
            90,
            90,
            90
        )

        self.cell(
            w - 4,
            3.5,
            str(label),
            0,
            1,
            "L"
        )

        self.set_xy(
            x + 2,
            y + 5.5
        )

        self.set_font(
            self.font_name,
            "B",
            11
        )

        self.set_text_color(
            0,
            51,
            102
        )

        self.cell(
            w - 4,
            6,
            str(value),
            0,
            1,
            "L"
        )

        if delta:

            self.set_xy(
                x + 2,
                y + 12
            )

            self.set_font(
                self.font_name,
                "",
                7.5
            )

            self.set_text_color(
                80,
                80,
                80
            )

            self.cell(
                w - 4,
                4,
                str(delta),
                0,
                1,
                "L"
            )


    # ========================================================================
    # TABLE
    # ========================================================================

    def simple_table(
        self,
        headers,
        rows,
        col_widths=None,
        font_size=8,
        row_h=5.5,
        align_first_left=True,
        max_rows=None,
        highlight_last=False
    ):

        if not headers:
            return

        if col_widths is None:

            col_widths = [
                CONTENT_WIDTH / len(headers)
            ] * len(headers)

        if self.get_y() > 250:
            self.add_page()

        data_rows = (
            rows
            if max_rows is None
            else rows[:max_rows]
        )

        def print_header():

            self.set_font(
                self.font_name,
                "B",
                font_size
            )

            self.set_fill_color(
                11,
                94,
                215
            )

            self.set_text_color(
                255,
                255,
                255
            )

            self.set_draw_color(
                180,
                200,
                220
            )

            for i, h in enumerate(headers):

                self.cell(
                    col_widths[i],
                    row_h + 1,
                    f" {str(h)}",
                    1,
                    0,
                    "C",
                    fill=True
                )

            self.ln()

        print_header()

        self.set_font(
            self.font_name,
            "",
            font_size
        )

        self.set_text_color(
            30,
            30,
            30
        )

        for idx, row in enumerate(data_rows):

            if self.get_y() > 275:

                self.add_page()

                print_header()

                self.set_font(
                    self.font_name,
                    "",
                    font_size
                )

                self.set_text_color(
                    30,
                    30,
                    30
                )

            is_last = (
                highlight_last and
                idx == len(data_rows) - 1
            )

            if is_last:

                self.set_fill_color(
                    255,
                    243,
                    205
                )

            elif idx % 2 == 0:

                self.set_fill_color(
                    248,
                    250,
                    253
                )

            else:

                self.set_fill_color(
                    255,
                    255,
                    255
                )

            for i in range(len(headers)):

                if i < len(row):

                    value = row[i]

                else:

                    value = ""

                align = (
                    "L"
                    if (
                        i == 0 and
                        align_first_left
                    )
                    else "C"
                )

                self.cell(
                    col_widths[i],
                    row_h,
                    f" {str(value)}",
                    1,
                    0,
                    align,
                    fill=True
                )

            self.ln()

        self.ln(1)


    # ========================================================================
    # ALERT CARD
    # ========================================================================

    def alert_card(
        self,
        idx,
        title,
        status,
        latest,
        change,
        advice
    ):

        if self.get_y() > 245:
            self.add_page()

        s = str(status).upper()

        if "CRIT" in s:

            border = (211, 47, 47)
            bg = (255, 242, 242)
            txt = (180, 0, 0)
            label = "วิกฤต (CRITICAL) - ต้องสั่งการด่วน"

        elif "WARN" in s:

            border = (245, 124, 0)
            bg = (255, 248, 240)
            txt = (200, 90, 0)
            label = "เฝ้าระวัง (WARNING) - ติดตามใกล้ชิด"

        else:

            border = (46, 125, 50)
            bg = (240, 248, 240)
            txt = (0, 100, 0)
            label = "ปกติ (NORMAL) - ดำเนินการตามแผน"

        self.set_draw_color(*border)
        self.set_fill_color(*bg)

        self.set_font(
            self.font_name,
            "B",
            9
        )

        self.set_text_color(*txt)

        self.cell(
            CONTENT_WIDTH,
            6,
            f"  [{idx}]  {title}",
            "LTR",
            1,
            "L",
            fill=True
        )

        self.set_font(
            self.font_name,
            "",
            8
        )

        self.set_text_color(
            50,
            50,
            50
        )

        self.cell(
            CONTENT_WIDTH,
            5,
            f"      สถานะ: {label}   |   "
            f"ล่าสุด: {latest}   |   "
            f"เปลี่ยนแปลง: {change}",
            "LR",
            1,
            "L",
            fill=True
        )

        self.set_font(
            self.font_name,
            "",
            7.5
        )

        self.set_text_color(
            30,
            70,
            120
        )

        self.multi_cell(
            CONTENT_WIDTH,
            4.5,
            f"      แนวทาง: {advice}",
            border="LBR",
            fill=True
        )

        self.ln(2)


    # ========================================================================
    # IMAGE
    # ========================================================================

    def image_block(
        self,
        png_path,
        w=178,
        caption=None
    ):

        if not png_path:
            return

        if self.get_y() > 220:
            self.add_page()

        try:

            self.image(
                png_path,
                w=w,
                x=(PAGE_WIDTH - w) / 2
            )

            self.ln(1)

            if caption:
                self.note(caption)

            self.ln(2)

        except Exception as e:

            self.note(
                f"(ไม่สามารถแสดงรูปภาพได้: {e})",
                color=(180, 0, 0)
            )


# ============================================================================
# MATPLOTLIB GRAPH HELPERS
# ============================================================================

def _new_fig(w=9, h=3.6):

    fig, ax = plt.subplots(
        figsize=(w, h)
    )

    return fig, ax


def _save(fig):

    tf = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".png"
    )

    path = tf.name

    tf.close()

    try:

        fig.tight_layout()

        fig.savefig(
            path,
            bbox_inches="tight",
            dpi=130
        )

    finally:

        plt.close(fig)

    return path


# ============================================================================
# LINE CHART
# ============================================================================

def chart_line(
    x,
    ys,
    labels,
    title,
    ylabel="",
    markers=True,
    color_list=None
):

    fig, ax = _new_fig(
        9,
        3.6
    )

    default_colors = [
        "#0B5ED7",
        "#F57C00",
        "#2E7D32",
        "#D32F2F",
        "#6A1B9A",
    ]

    colors = (
        color_list
        if color_list
        else default_colors
    )

    for i, (y, label) in enumerate(
        zip(ys, labels)
    ):

        ax.plot(
            x,
            y,
            marker="o" if markers else None,
            label=label,
            color=colors[i % len(colors)],
            linewidth=2
        )

    ax.set_title(
        title,
        fontsize=10
    )

    ax.set_ylabel(
        ylabel,
        fontsize=8
    )

    ax.grid(
        True,
        alpha=0.3,
        linestyle="--"
    )

    ax.tick_params(
        axis="x",
        rotation=30,
        labelsize=7
    )

    ax.tick_params(
        axis="y",
        labelsize=7
    )

    if labels:
        ax.legend(
            fontsize=7.5,
            loc="best"
        )

    return _save(fig)


# ============================================================================
# BAR CHART
# ============================================================================

def chart_bar(
    x,
    y,
    title,
    ylabel="",
    color="#0B5ED7",
    text_fmt=None
):

    fig, ax = _new_fig(
        9,
        3.6
    )

    bars = ax.bar(
        x,
        y,
        color=color,
        edgecolor="white"
    )

    if text_fmt:

        for b, v in zip(
            bars,
            y
        ):

            ax.text(
                b.get_x() +
                b.get_width() / 2,
                b.get_height(),
                text_fmt.format(v),
                ha="center",
                va="bottom",
                fontsize=7
            )

    ax.set_title(
        title,
        fontsize=10
    )

    ax.set_ylabel(
        ylabel,
        fontsize=8
    )

    ax.grid(
        True,
        axis="y",
        alpha=0.3,
        linestyle="--"
    )

    ax.tick_params(
        axis="x",
        rotation=30,
        labelsize=7
    )

    ax.tick_params(
        axis="y",
        labelsize=7
    )

    return _save(fig)


# ============================================================================
# GROUPED BAR
# ============================================================================

def chart_bar_grouped(
    x,
    ys,
    labels,
    title,
    ylabel="",
    color_list=None
):

    import numpy as np

    fig, ax = _new_fig(
        9,
        3.6
    )

    default_colors = [
        "#0B5ED7",
        "#F57C00",
        "#2E7D32",
        "#D32F2F",
    ]

    colors = (
        color_list
        if color_list
        else default_colors
    )

    n = len(ys)

    xx = np.arange(
        len(x)
    )

    w = 0.8 / max(n, 1)

    for i, (y, label) in enumerate(
        zip(ys, labels)
    ):

        ax.bar(
            xx +
            (i - n / 2 + 0.5) * w,
            y,
            width=w,
            label=label,
            color=colors[i % len(colors)]
        )

    ax.set_xticks(xx)

    ax.set_xticklabels(
        x,
        rotation=30,
        fontsize=7
    )

    ax.set_title(
        title,
        fontsize=10
    )

    ax.set_ylabel(
        ylabel,
        fontsize=8
    )

    ax.grid(
        True,
        axis="y",
        alpha=0.3,
        linestyle="--"
    )

    ax.tick_params(
        axis="y",
        labelsize=7
    )

    ax.legend(
        fontsize=7.5
    )

    return _save(fig)


# ============================================================================
# PIE CHART
# ============================================================================

def chart_pie(
    values,
    labels,
    title,
    hole=0.35
):

    fig, ax = plt.subplots(
        figsize=(7, 3.8)
    )

    wedges, texts, autotexts = ax.pie(
        values,
        labels=labels,
        autopct="%1.1f%%",
        startangle=90,
        wedgeprops=dict(
            width=(
                0.65
                if hole
                else 1.0
            ),
            edgecolor="white"
        ),
        textprops={
            "fontsize": 7
        }
    )

    for t in autotexts:

        t.set_fontsize(7)
        t.set_color("white")

    ax.set_title(
        title,
        fontsize=10
    )

    ax.axis("equal")

    return _save(fig)


# ============================================================================
# HORIZONTAL BAR
# ============================================================================

def chart_hbar(
    x,
    y,
    title,
    xlabel=""
):

    fig, ax = _new_fig(
        9,
        max(
            3.5,
            0.25 * len(y)
        )
    )

    ax.barh(
        x,
        y,
        color="#0B5ED7"
    )

    ax.set_title(
        title,
        fontsize=10
    )

    ax.set_xlabel(
        xlabel,
        fontsize=8
    )

    ax.grid(
        True,
        axis="x",
        alpha=0.3,
        linestyle="--"
    )

    ax.tick_params(
        labelsize=7
    )

    return _save(fig)


# ============================================================================
# MAIN PDF GENERATOR
# ============================================================================

def generate_pdf_report(
    latest_month,
    username,
    data,
    alerts_df,
    options
):
    """
    สร้างรายงาน PDF Easy Pass Executive Report

    Parameters
    ----------
    latest_month : str
        เดือนล่าสุด

    username : str
        ชื่อผู้ใช้งาน

    data : dict
        Dictionary ของ DataFrame

    alerts_df : DataFrame
        Early Warning DataFrame

    options : dict
        ตัวเลือก section
    """

    pdf = ExecutivePDF(
        latest_month,
        username
    )

    f = pdf.font_name

    temp_files = []

    # ========================================================================
    # PAGE 1
    # ========================================================================

    try:

        pdf.add_page()

        # --------------------------------------------------------------------
        # Cover Banner
        # --------------------------------------------------------------------

        pdf.set_fill_color(
            0,
            51,
            102
        )

        pdf.rect(
            0,
            0,
            PAGE_WIDTH,
            40,
            "F"
        )

        pdf.set_xy(
            12,
            8
        )

        pdf.set_font(
            f,
            "B",
            18
        )

        pdf.set_text_color(
            255,
            255,
            255
        )

        pdf.cell(
            0,
            10,
            "EASY PASS Executive Report",
            0,
            1,
            "L"
        )

        pdf.set_x(12)

        pdf.set_font(
            f,
            "",
            11
        )

        pdf.set_text_color(
            200,
            220,
            245
        )

        pdf.cell(
            0,
            6,
            "รายงานสรุปผู้บริหาร ระบบเก็บค่าผ่านทางพิเศษอัตโนมัติ (Easy Pass)",
            0,
            1,
            "L"
        )

        pdf.set_x(12)

        pdf.set_font(
            f,
            "",
            10
        )

        pdf.cell(
            0,
            6,
            "การทางพิเศษแห่งประเทศไทย (กทพ.)",
            0,
            1,
            "L"
        )

        pdf.set_x(12)

        pdf.set_font(
            f,
            "B",
            11
        )

        pdf.set_text_color(
            255,
            220,
            100
        )

        pdf.cell(
            0,
            6,
            f"ประจำเดือน: {latest_month} | ปีงบประมาณ 2569",
            0,
            1,
            "L"
        )

        # --------------------------------------------------------------------
        # Metadata
        # --------------------------------------------------------------------

        pdf.set_y(48)

        pdf.set_font(
            f,
            "",
            9
        )

        pdf.set_text_color(
            80,
            80,
            80
        )

        pdf.cell(
            0,
            5,
            f"ผู้จัดทำระบบรายงาน: {username}",
            0,
            1,
            "L"
        )

        pdf.cell(
            0,
            5,
            "วันที่จัดทำ: "
            + datetime.now().strftime(
                "%d/%m/%Y %H:%M"
            ),
            0,
            1,
            "L"
        )

        pdf.ln(4)

        # ====================================================================
        # 1. EXECUTIVE SUMMARY
        # ====================================================================

        if options.get(
            "summary",
            True
        ):

            reg = data.get("reg")
            etc = data.get("etc")
            topup_total = data.get("topup_total")
            card_status = data.get("card_status")
            cs = data.get("cs")
            anomaly = data.get("anomaly")

            pdf.section_title(
                "1",
                "บทสรุปผู้บริหาร (Executive Summary)"
            )

            # ---------------------------------------------------------------
            # KPI values
            # ---------------------------------------------------------------

            cumulative_total = _safe_last(
                reg,
                "cumulative_total"
            )

            new_registrations = _safe_last(
                reg,
                "new_registrations"
            )

            active_cards = _safe_last(
                card_status,
                "active_cards"
            )

            active_cards_prev = _safe_previous(
                card_status,
                "active_cards"
            )

            etc_percent = _safe_last(
                etc,
                "etc_percent"
            )

            etc_percent_prev = _safe_previous(
                etc,
                "etc_percent"
            )

            total_baht = _safe_last(
                topup_total,
                "total_baht"
            )

            total_baht_prev = _safe_previous(
                topup_total,
                "total_baht"
            )

            traffic = _safe_last(
                etc,
                "total_traffic_million"
            )

            traffic_prev = _safe_previous(
                etc,
                "total_traffic_million"
            )

            anomaly_total = _safe_last(
                anomaly,
                "total_events"
            )

            anomaly_prev = _safe_previous(
                anomaly,
                "total_events"
            )

            lost_count = _safe_last(
                card_status,
                "lost_count"
            )

            lost_prev = _safe_previous(
                card_status,
                "lost_count"
            )

            total_cases = _safe_last(
                cs,
                "total_cases"
            )

            total_cases_prev = _safe_previous(
                cs,
                "total_cases"
            )

            kpis = [

                {
                    "label": "ยอดสมัครสะสมทั้งหมด",
                    "value":
                        f"{_fmt_number(cumulative_total)} บัตร",
                    "delta":
                        f"เดือนนี้ +{_fmt_number(new_registrations)}"
                },

                {
                    "label": "บัตร Active",
                    "value":
                        f"{_fmt_number(active_cards)}",
                    "delta":
                        f"{_delta(active_cards, active_cards_prev):+,.0f}"
                },

                {
                    "label": "สัดส่วนจราจร ETC",
                    "value":
                        f"{_fmt_number(etc_percent, 2)}%",
                    "delta":
                        f"{_delta(etc_percent, etc_percent_prev):+.2f} pp"
                },

                {
                    "label": "ยอดเติมเงินเดือนนี้",
                    "value":
                        f"{_safe_float(total_baht) / 1e6:,.1f} ลบ.",
                    "delta":
                        f"{_pct_change(total_baht, total_baht_prev):+.1f}%"
                },

                {
                    "label": "ปริมาณจราจรรวม",
                    "value":
                        f"{_fmt_number(traffic, 2)} ล้านคัน",
                    "delta":
                        f"{_pct_change(traffic, traffic_prev):+.1f}%"
                },

                {
                    "label": "เหตุการณ์ไม้กั้นไม่เปิด",
                    "value":
                        f"{_fmt_number(anomaly_total)}",
                    "delta":
                        f"{_pct_change(anomaly_total, anomaly_prev):+.1f}%"
                },

                {
                    "label": "บัตรสูญหายสะสม",
                    "value":
                        f"{_fmt_number(lost_count)} บัตร",
                    "delta":
                        f"{_delta(lost_count, lost_prev):+,.0f}"
                },

                {
                    "label": "เรื่องร้องเรียน CS",
                    "value":
                        f"{_fmt_number(total_cases)} เรื่อง",
                    "delta":
                        f"{_delta(total_cases, total_cases_prev):+,.0f}"
                },
            ]

            pdf.kpi_row(
                kpis,
                per_row=4
            )

            # ---------------------------------------------------------------
            # Early Warning Snapshot
            # ---------------------------------------------------------------

            if (
                alerts_df is not None
                and not alerts_df.empty
            ):

                if "สถานะ" in alerts_df.columns:

                    n_crit = (
                        alerts_df["สถานะ"]
                        .astype(str)
                        .str.upper()
                        .eq("CRITICAL")
                        .sum()
                    )

                    n_warn = (
                        alerts_df["สถานะ"]
                        .astype(str)
                        .str.upper()
                        .eq("WARNING")
                        .sum()
                    )

                    n_norm = (
                        alerts_df["สถานะ"]
                        .astype(str)
                        .str.upper()
                        .eq("NORMAL")
                        .sum()
                    )

                else:

                    n_crit = 0
                    n_warn = 0
                    n_norm = 0

                pdf.set_font(
                    f,
                    "B",
                    9.5
                )

                pdf.set_text_color(
                    0,
                    51,
                    102
                )

                pdf.cell(
                    0,
                    6,
                    "สรุปสถานะการเฝ้าระวัง (Early Warning Snapshot)",
                    0,
                    1,
                    "L"
                )

                pdf.set_font(
                    f,
                    "",
                    8.5
                )

                pdf.set_text_color(
                    150,
                    0,
                    0
                )

                pdf.cell(
                    62,
                    6,
                    f"วิกฤต (CRITICAL): {n_crit}",
                    0,
                    0,
                    "L"
                )

                pdf.set_text_color(
                    200,
                    90,
                    0
                )

                pdf.cell(
                    62,
                    6,
                    f"เฝ้าระวัง (WARNING): {n_warn}",
                    0,
                    0,
                    "L"
                )

                pdf.set_text_color(
                    0,
                    120,
                    0
                )

                pdf.cell(
                    0,
                    6,
                    f"ปกติ (NORMAL): {n_norm}",
                    0,
                    1,
                    "L"
                )

                pdf.set_text_color(
                    40,
                    40,
                    40
                )

                pdf.ln(2)


        # ====================================================================
        # 2. EARLY WARNING
        # ====================================================================

        if (
            options.get("warning", True)
            and alerts_df is not None
            and not alerts_df.empty
        ):

            pdf.add_page()

            pdf.section_title(
                "2",
                "ศูนย์เฝ้าระวังความผิดปกติ (Early Warning Center)"
            )

            required_alert_cols = [
                "สถานะ",
                "หัวข้อ",
                "ค่าล่าสุด",
                "เดือนก่อน",
                "เปลี่ยนแปลง",
                "คำแนะนำ"
            ]

            if all(
                c in alerts_df.columns
                for c in required_alert_cols
            ):

                headers = [
                    "#",
                    "หัวข้อ",
                    "ค่าล่าสุด",
                    "ค่าอ้างอิง",
                    "เปลี่ยนแปลง",
                    "สถานะ"
                ]

                widths = [
                    8,
                    62,
                    30,
                    30,
                    25,
                    31
                ]

                rows = []

                for i, (_, r) in enumerate(
                    alerts_df.iterrows(),
                    1
                ):

                    status = str(
                        r["สถานะ"]
                    ).upper()

                    badge = {
                        "CRITICAL": "วิกฤต",
                        "WARNING": "เฝ้าระวัง",
                        "NORMAL": "ปกติ"
                    }.get(
                        status,
                        status
                    )

                    rows.append([
                        str(i),
                        r["หัวข้อ"],
                        r["ค่าล่าสุด"],
                        r["เดือนก่อน"],
                        r["เปลี่ยนแปลง"],
                        badge
                    ])

                pdf.simple_table(
                    headers,
                    rows,
                    col_widths=widths,
                    font_size=8
                )

                pdf.ln(3)

                pdf.sub_title(
                    "รายละเอียดเชิงบริหาร (การ์ดแจ้งเตือน)"
                )

                for i, (_, r) in enumerate(
                    alerts_df.iterrows(),
                    1
                ):

                    pdf.alert_card(
                        i,
                        r["หัวข้อ"],
                        r["สถานะ"],
                        r["ค่าล่าสุด"],
                        r["เปลี่ยนแปลง"],
                        r["คำแนะนำ"]
                    )


        # ====================================================================
        # 3. REGISTRATION
        # ====================================================================

        if options.get("reg", True):

            reg = data.get("reg")
            reg_by_route = data.get(
                "reg_by_route"
            )

            if reg is not None and not reg.empty:

                pdf.add_page()

                pdf.section_title(
                    "3",
                    "ยอดสมัครใช้บัตร Easy Pass"
                )

                # ------------------------------------------------------------
                # Chart
                # ------------------------------------------------------------

                if all(
                    c in reg.columns
                    for c in [
                        "month_label",
                        "new_registrations"
                    ]
                ):

                    fig_path = chart_bar(
                        reg["month_label"].tolist(),
                        reg["new_registrations"].tolist(),
                        "ยอดสมัครใช้บัตร Easy Pass รายเดือน ปีงบประมาณ 2569",
                        ylabel="บัตร",
                        text_fmt="{:,.0f}"
                    )

                    temp_files.append(
                        fig_path
                    )

                    pdf.image_block(
                        fig_path,
                        w=178
                    )

                    pdf.note(
                        "ที่มา: บบ. กบด. ฝตท.1"
                    )

                # ------------------------------------------------------------
                # Table
                # ------------------------------------------------------------

                required = [
                    "month_label",
                    "new_registrations",
                    "cumulative_total"
                ]

                if all(
                    c in reg.columns
                    for c in required
                ):

                    headers = [
                        "เดือน",
                        "สมัครใหม่ (บัตร)",
                        "สะสมทั้งหมด (บัตร)"
                    ]

                    rows = [
                        [
                            r["month_label"],
                            f"{_safe_float(r['new_registrations']):,.0f}",
                            f"{_safe_float(r['cumulative_total']):,.0f}"
                        ]
                        for _, r in reg.iterrows()
                    ]

                    pdf.simple_table(
                        headers,
                        rows,
                        col_widths=[
                            60,
                            65,
                            65
                        ],
                        font_size=8.5
                    )

                # ------------------------------------------------------------
                # Route table
                # ------------------------------------------------------------

                if (
                    reg_by_route is not None
                    and not reg_by_route.empty
                ):

                    pdf.ln(3)

                    pdf.sub_title(
                        "ยอดจำหน่ายบัตร Easy Pass แยกตามสายทาง (เฉพาะเดือน ส.ค. 69)"
                    )

                    headers = [
                        "รหัส",
                        "สายทาง",
                        "เดือน ส.ค. 69",
                        "ปีงบ 69 สะสม",
                        "ตั้งแต่เริ่มจำหน่าย"
                    ]

                    rows = []

                    for _, r in reg_by_route.iterrows():

                        rows.append([
                            r.get(
                                "route_code",
                                ""
                            ),
                            r.get(
                                "route_name",
                                ""
                            ),
                            _fmt_number(
                                r.get(
                                    "monthly_aug69",
                                    0
                                )
                            ),
                            _fmt_number(
                                r.get(
                                    "fy69_cumulative",
                                    0
                                )
                            ),
                            _fmt_number(
                                r.get(
                                    "since_start",
                                    0
                                )
                            )
                        ])

                    pdf.simple_table(
                        headers,
                        rows,
                        col_widths=[
                            12,
                            65,
                            38,
                            38,
                            37
                        ],
                        font_size=8,
                        highlight_last=True
                    )


        # ====================================================================
        # 4. INVENTORY
        # ====================================================================

        if options.get("inv", True):

            inv = data.get("inv")
            inv_by_route = data.get(
                "inv_by_route"
            )

            if inv is not None and not inv.empty:

                pdf.add_page()

                pdf.section_title(
                    "4",
                    "ยอดคงเหลือบัตร Easy Pass ในคลัง"
                )

                required = [
                    "month_label",
                    "obu_stock",
                    "smartcard_stock"
                ]

                if all(
                    c in inv.columns
                    for c in required
                ):

                    fig_path = chart_line(
                        inv["month_label"].tolist(),
                        [
                            inv["obu_stock"].tolist(),
                            inv["smartcard_stock"].tolist()
                        ],
                        [
                            "OBU (ใบ)",
                            "Smart Card (ใบ)"
                        ],
                        "แนวโน้มยอดคงเหลือบัตรในคลัง ปีงบประมาณ 2569",
                        ylabel="จำนวน (ใบ)"
                    )

                    temp_files.append(
                        fig_path
                    )

                    pdf.image_block(
                        fig_path,
                        w=178
                    )

                    headers = [
                        "เดือน",
                        "OBU คงเหลือ (ใบ)",
                        "Smart Card คงเหลือ (ใบ)"
                    ]

                    rows = [
                        [
                            r["month_label"],
                            _fmt_number(
                                r["obu_stock"]
                            ),
                            _fmt_number(
                                r["smartcard_stock"]
                            )
                        ]
                        for _, r in inv.iterrows()
                    ]

                    pdf.simple_table(
                        headers,
                        rows,
                        col_widths=[
                            60,
                            65,
                            65
                        ],
                        font_size=8.5
                    )

                if (
                    inv_by_route is not None
                    and not inv_by_route.empty
                ):

                    pdf.ln(3)

                    pdf.sub_title(
                        "ยอดคงเหลือ ณ วันที่ 31 สิงหาคม 2569 แยกตามสายทาง"
                    )

                    headers = [
                        "สายทาง",
                        "OBU (ใบ)",
                        "Smart Card (ใบ)"
                    ]

                    rows = [
                        [
                            r.get(
                                "route_name",
                                ""
                            ),
                            _fmt_number(
                                r.get(
                                    "obu_stock",
                                    0
                                )
                            ),
                            _fmt_number(
                                r.get(
                                    "smartcard_stock",
                                    0
                                )
                            )
                        ]
                        for _, r in inv_by_route.iterrows()
                    ]

                    pdf.simple_table(
                        headers,
                        rows,
                        col_widths=[
                            90,
                            50,
                            50
                        ],
                        font_size=8.5,
                        highlight_last=True
                    )


        # ====================================================================
        # 5. TRAFFIC / ETC
        # ====================================================================

        if options.get("traffic", True):

            etc = data.get("etc")
            traffic_full = data.get(
                "traffic_full"
            )

            if etc is not None and not etc.empty:

                pdf.add_page()

                pdf.section_title(
                    "5",
                    "ปริมาณจราจรและระบบ ETC"
                )

                required = [
                    "month_label",
                    "etc_percent"
                ]

                if all(
                    c in etc.columns
                    for c in required
                ):

                    fig_path = chart_line(
                        etc["month_label"].tolist(),
                        [
                            etc["etc_percent"].tolist()
                        ],
                        [
                            "ร้อยละ ETC"
                        ],
                        "ร้อยละปริมาณจราจรผ่านระบบ ETC ปีงบประมาณ 2569",
                        ylabel="ร้อยละ (%)"
                    )

                    temp_files.append(
                        fig_path
                    )

                    pdf.image_block(
                        fig_path,
                        w=178
                    )

                required = [
                    "month_label",
                    "total_traffic_million",
                    "etc_traffic_million",
                    "etc_percent"
                ]

                if all(
                    c in etc.columns
                    for c in required
                ):

                    headers = [
                        "เดือน",
                        "จราจรรวม (ล้านคัน)",
                        "ETC (ล้านคัน)",
                        "ร้อยละ ETC"
                    ]

                    rows = [
                        [
                            r["month_label"],
                            _fmt_number(
                                r["total_traffic_million"],
                                2
                            ),
                            _fmt_number(
                                r["etc_traffic_million"],
                                2
                            ),
                            _fmt_percent(
                                r["etc_percent"],
                                2
                            )
                        ]
                        for _, r in etc.iterrows()
                    ]

                    pdf.simple_table(
                        headers,
                        rows,
                        col_widths=[
                            50,
                            50,
                            45,
                            45
                        ],
                        font_size=8.5
                    )

                if (
                    traffic_full is not None
                    and not traffic_full.empty
                ):

                    pdf.add_page()

                    pdf.sub_title(
                        "ตารางรายละเอียดปริมาณจราจร แยกรายสายทาง (เฉพาะเดือน ส.ค. 69)"
                    )

                    headers = [
                        "สายทาง",
                        "โซน",
                        "จราจรรวม",
                        "% Easy Pass",
                        "% EMV"
                    ]

                    rows = []

                    for _, r in traffic_full.iterrows():

                        rows.append([
                            r.get(
                                "route_name",
                                ""
                            ),
                            r.get(
                                "zone",
                                ""
                            ),
                            _fmt_number(
                                r.get(
                                    "total_traffic",
                                    0
                                )
                            ),
                            _fmt_percent(
                                r.get(
                                    "percent_easypass",
                                    0
                                )
                            ),
                            _fmt_percent(
                                r.get(
                                    "emv_percent",
                                    0
                                )
                            )
                        ])

                    pdf.simple_table(
                        headers,
                        rows,
                        col_widths=[
                            70,
                            25,
                            40,
                            30,
                            25
                        ],
                        font_size=8,
                        highlight_last=True
                    )


        # ====================================================================
        # 6. ANOMALY
        # ====================================================================

        if options.get("anomaly", True):

            anomaly = data.get(
                "anomaly"
            )

            if (
                anomaly is not None
                and not anomaly.empty
            ):

                pdf.add_page()

                pdf.section_title(
                    "6",
                    "เหตุการณ์ไม้กั้นไม่เปิด (Anomaly Events)"
                )

                required = [
                    "month_label",
                    "total_events"
                ]

                if all(
                    c in anomaly.columns
                    for c in required
                ):

                    fig_path = chart_line(
                        anomaly["month_label"].tolist(),
                        [
                            anomaly["total_events"].tolist()
                        ],
                        [
                            "เหตุการณ์ไม้กั้นไม่เปิด"
                        ],
                        "แนวโน้มเหตุการณ์ไม้กั้นไม่เปิด ปีงบประมาณ 2569",
                        ylabel="ครั้ง",
                        color_list=[
                            "#D32F2F"
                        ]
                    )

                    temp_files.append(
                        fig_path
                    )

                    pdf.image_block(
                        fig_path,
                        w=178
                    )

                headers = [
                    "เดือน",
                    "รวม (ครั้ง)",
                    "ติดตั้งผิด",
                    "ไม่พบข้อมูลเข้า",
                    "เงินไม่พอ",
                    "Blacklist",
                    "อุปกรณ์"
                ]

                rows = []

                for _, r in anomaly.iterrows():

                    rows.append([
                        r.get(
                            "month_label",
                            ""
                        ),
                        _fmt_number(
                            r.get(
                                "total_events",
                                0
                            )
                        ),
                        _fmt_number(
                            r.get(
                                "cause_install",
                                0
                            )
                        ),
                        _fmt_number(
                            r.get(
                                "cause_no_entry_data",
                                0
                            )
                        ),
                        _fmt_number(
                            r.get(
                                "cause_low_balance",
                                0
                            )
                        ),
                        _fmt_number(
                            r.get(
                                "cause_blacklist",
                                0
                            )
                        ),
                        _fmt_number(
                            r.get(
                                "cause_equipment",
                                0
                            )
                        )
                    ])

                pdf.simple_table(
                    headers,
                    rows,
                    col_widths=[
                        22,
                        30,
                        26,
                        30,
                        26,
                        28,
                        28
                    ],
                    font_size=7.5
                )


        # ====================================================================
        # 7. EMV
        # ====================================================================

        if options.get("emv", True):

            emv = data.get(
                "emv"
            )

            if (
                emv is not None
                and not emv.empty
            ):

                pdf.add_page()

                pdf.section_title(
                    "7",
                    "ปริมาณจราจร EMV"
                )

                if all(
                    c in emv.columns
                    for c in [
                        "month_label",
                        "emv_percent"
                    ]
                ):

                    fig_path = chart_line(
                        emv["month_label"].tolist(),
                        [
                            emv["emv_percent"].tolist()
                        ],
                        [
                            "ร้อยละ EMV"
                        ],
                        "ร้อยละปริมาณจราจร EMV ปีงบประมาณ 2569",
                        ylabel="ร้อยละ (%)",
                        color_list=[
                            "#6A1B9A"
                        ]
                    )

                    temp_files.append(
                        fig_path
                    )

                    pdf.image_block(
                        fig_path,
                        w=178
                    )

                required = [
                    "month_label",
                    "total_traffic_million",
                    "emv_traffic_million",
                    "emv_percent"
                ]

                if all(
                    c in emv.columns
                    for c in required
                ):

                    headers = [
                        "เดือน",
                        "จราจรรวม (ล้านคัน)",
                        "EMV (ล้านคัน)",
                        "ร้อยละ EMV"
                    ]

                    rows = [
                        [
                            r["month_label"],
                            _fmt_number(
                                r["total_traffic_million"],
                                2
                            ),
                            _fmt_number(
                                r["emv_traffic_million"],
                                2
                            ),
                            _fmt_percent(
                                r["emv_percent"]
                            )
                        ]
                        for _, r in emv.iterrows()
                    ]

                    pdf.simple_table(
                        headers,
                        rows,
                        col_widths=[
                            50,
                            50,
                            45,
                            45
                        ],
                        font_size=8.5
                    )


        # ====================================================================
        # 8. MOTORWAY
        # ====================================================================

        if options.get("motorway", True):

            motorway = data.get(
                "motorway"
            )

            route_detail = data.get(
                "route_detail"
            )

            mpass = data.get(
                "mpass_detail"
            )

            if (
                motorway is not None
                and not motorway.empty
            ):

                pdf.add_page()

                pdf.section_title(
                    "8",
                    "มอเตอร์เวย์และดอนเมืองโทลล์เวย์"
                )

                required = [
                    "month_label",
                    "motorway_transactions",
                    "donmuang_tollway_transactions"
                ]

                if all(
                    c in motorway.columns
                    for c in required
                ):

                    fig_path = chart_line(
                        motorway["month_label"].tolist(),
                        [
                            motorway["motorway_transactions"].tolist(),
                            motorway["donmuang_tollway_transactions"].tolist()
                        ],
                        [
                            "มอเตอร์เวย์",
                            "ดอนเมืองโทลล์เวย์"
                        ],
                        "ปริมาณธุรกรรม Easy Pass ผ่านมอเตอร์เวย์และดอนเมืองโทลล์เวย์",
                        ylabel="ธุรกรรม"
                    )

                    temp_files.append(
                        fig_path
                    )

                    pdf.image_block(
                        fig_path,
                        w=178
                    )

                headers = [
                    "เดือน",
                    "มอเตอร์เวย์ (ธุรกรรม)",
                    "ดอนเมืองโทลล์เวย์ (ธุรกรรม)"
                ]

                rows = [
                    [
                        r.get(
                            "month_label",
                            ""
                        ),
                        _fmt_number(
                            r.get(
                                "motorway_transactions",
                                0
                            )
                        ),
                        _fmt_number(
                            r.get(
                                "donmuang_tollway_transactions",
                                0
                            )
                        )
                    ]
                    for _, r in motorway.iterrows()
                ]

                pdf.simple_table(
                    headers,
                    rows,
                    col_widths=[
                        50,
                        70,
                        70
                    ],
                    font_size=8.5
                )

            if (
                route_detail is not None
                and not route_detail.empty
            ):

                pdf.ln(3)

                pdf.sub_title(
                    "ปริมาณธุรกรรม Easy Pass: สายทาง กทพ. vs กรมทางหลวง"
                )

                headers = [
                    "เดือน",
                    "กทพ. (เที่ยว)",
                    "ม6 (เที่ยว)",
                    "ม7 (เที่ยว)",
                    "ม81 (เที่ยว)"
                ]

                rows = [
                    [
                        r.get(
                            "month_label",
                            ""
                        ),
                        _fmt_number(
                            r.get(
                                "exat_total_transactions",
                                0
                            )
                        ),
                        _fmt_number(
                            r.get(
                                "doh_m6_transactions",
                                0
                            )
                        ),
                        _fmt_number(
                            r.get(
                                "doh_m7_transactions",
                                0
                            )
                        ),
                        _fmt_number(
                            r.get(
                                "doh_m81_transactions",
                                0
                            )
                        )
                    ]
                    for _, r in route_detail.iterrows()
                ]

                pdf.simple_table(
                    headers,
                    rows,
                    col_widths=[
                        40,
                        38,
                        38,
                        38,
                        36
                    ],
                    font_size=8
                )

            if (
                mpass is not None
                and not mpass.empty
            ):

                pdf.add_page()

                pdf.sub_title(
                    "M-Pass vs Easy Pass แยกสายทาง (เดือน ส.ค. 69)"
                )

                headers = [
                    "สายทาง",
                    "M-Pass",
                    "%",
                    "Easy Pass",
                    "%",
                    "รวม"
                ]

                rows = [
                    [
                        r.get(
                            "route_name",
                            ""
                        ),
                        _fmt_number(
                            r.get(
                                "mpass_transactions",
                                0
                            )
                        ),
                        _fmt_number(
                            r.get(
                                "mpass_percent",
                                0
                            ),
                            2
                        ),
                        _fmt_number(
                            r.get(
                                "easypass_transactions",
                                0
                            )
                        ),
                        _fmt_number(
                            r.get(
                                "easypass_percent",
                                0
                            ),
                            2
                        ),
                        _fmt_number(
                            r.get(
                                "total_transactions",
                                0
                            )
                        )
                    ]
                    for _, r in mpass.iterrows()
                ]

                pdf.simple_table(
                    headers,
                    rows,
                    col_widths=[
                        55,
                        30,
                        15,
                        35,
                        15,
                        40
                    ],
                    font_size=7.5,
                    highlight_last=True
                )


        # ====================================================================
        # 9. TOPUP
        # ====================================================================

        if options.get("topup", True):

            topup_total = data.get(
                "topup_total"
            )

            topup_ext = data.get(
                "topup_ext"
            )

            topup_edc = data.get(
                "topup_edc"
            )

            topup_channel = data.get(
                "topup_channel"
            )

            if (
                topup_total is not None
                and not topup_total.empty
            ):

                pdf.add_page()

                pdf.section_title(
                    "9",
                    "ยอดการเติมเงินสำรองค่าผ่านทาง"
                )

                if all(
                    c in topup_total.columns
                    for c in [
                        "month_label",
                        "total_baht"
                    ]
                ):

                    fig_path = chart_line(
                        topup_total["month_label"].tolist(),
                        [
                            topup_total["total_baht"].tolist()
                        ],
                        [
                            "ยอดเติมเงินรวม"
                        ],
                        "ยอดเติมเงินสำรองค่าผ่านทาง ปีงบประมาณ 2569 (บาท)",
                        ylabel="บาท",
                        color_list=[
                            "#2E7D32"
                        ]
                    )

                    temp_files.append(
                        fig_path
                    )

                    pdf.image_block(
                        fig_path,
                        w=178
                    )

                headers = [
                    "เดือน",
                    "รวม (บาท)",
                    "หน่วยงานภายนอก",
                    "ภายใน",
                    "ช่องทางอื่น"
                ]

                rows = [
                    [
                        r.get(
                            "month_label",
                            ""
                        ),
                        _fmt_baht(
                            r.get(
                                "total_baht",
                                0
                            )
                        ),
                        _fmt_baht(
                            r.get(
                                "external_agencies_baht",
                                0
                            )
                        ),
                        _fmt_baht(
                            r.get(
                                "internal_baht",
                                0
                            )
                        ),
                        _fmt_baht(
                            r.get(
                                "other_channel_baht",
                                0
                            )
                        )
                    ]
                    for _, r in topup_total.iterrows()
                ]

                pdf.simple_table(
                    headers,
                    rows,
                    col_widths=[
                        30,
                        50,
                        45,
                        35,
                        30
                    ],
                    font_size=7.5
                )

            if (
                topup_channel is not None
                and not topup_channel.empty
            ):

                pdf.ln(3)

                pdf.sub_title(
                    "สรุปยอดเติมเงิน แยกช่องทาง (เดือน ส.ค. 69)"
                )

                headers = [
                    "ช่องทาง",
                    "รายการ",
                    "%รายการ",
                    "จำนวนเงิน (บาท)",
                    "%เงิน"
                ]

                rows = [
                    [
                        r.get(
                            "channel",
                            ""
                        ),
                        _fmt_number(
                            r.get(
                                "transactions",
                                0
                            )
                        ),
                        _fmt_percent(
                            r.get(
                                "percent_transactions",
                                0
                            )
                        ),
                        _fmt_baht(
                            r.get(
                                "amount_baht",
                                0
                            )
                        ),
                        _fmt_percent(
                            r.get(
                                "percent_amount",
                                0
                            )
                        )
                    ]
                    for _, r in topup_channel.iterrows()
                ]

                pdf.simple_table(
                    headers,
                    rows,
                    col_widths=[
                        45,
                        35,
                        25,
                        45,
                        25
                    ],
                    font_size=8
                )

            if (
                topup_ext is not None
                and not topup_ext.empty
            ):

                pdf.add_page()

                pdf.sub_title(
                    "เติมเงินผ่านหน่วยงานภายนอก (Top 16)"
                )

                sorted_ext = (
                    topup_ext
                    .sort_values(
                        "amount_baht"
                    )
                )

                fig_path = chart_hbar(
                    sorted_ext["agency"].tolist(),
                    sorted_ext["amount_baht"].tolist(),
                    "ยอดเติมเงินผ่านหน่วยงานภายนอก (บาท)",
                    xlabel="บาท"
                )

                temp_files.append(
                    fig_path
                )

                pdf.image_block(
                    fig_path,
                    w=178
                )

                headers = [
                    "หน่วยงาน",
                    "ยอดเติมเงิน (บาท)",
                    "สัดส่วน (%)"
                ]

                rows = [
                    [
                        r.get(
                            "agency",
                            ""
                        ),
                        _fmt_baht(
                            r.get(
                                "amount_baht",
                                0
                            )
                        ),
                        _fmt_percent(
                            r.get(
                                "share_percent",
                                0
                            )
                        )
                    ]
                    for _, r in topup_ext.iterrows()
                ]

                pdf.simple_table(
                    headers,
                    rows,
                    col_widths=[
                        90,
                        55,
                        45
                    ],
                    font_size=8
                )

            if (
                topup_edc is not None
                and not topup_edc.empty
            ):

                pdf.add_page()

                pdf.sub_title(
                    "ยอดเติมเงินผ่านเครื่อง EDC แยกประเภท"
                )

                headers = [
                    "เดือน",
                    "เงินสด",
                    "บัตรเครดิต",
                    "บัตรเดบิต",
                    "QR Code"
                ]

                rows = [
                    [
                        r.get(
                            "month_label",
                            ""
                        ),
                        _fmt_baht(
                            r.get(
                                "cash_baht",
                                0
                            )
                        ),
                        _fmt_baht(
                            r.get(
                                "credit_baht",
                                0
                            )
                        ),
                        _fmt_baht(
                            r.get(
                                "debit_baht",
                                0
                            )
                        ),
                        _fmt_baht(
                            r.get(
                                "qr_baht",
                                0
                            )
                        )
                    ]
                    for _, r in topup_edc.iterrows()
                ]

                pdf.simple_table(
                    headers,
                    rows,
                    col_widths=[
                        30,
                        40,
                        40,
                        40,
                        40
                    ],
                    font_size=8
                )


        # ====================================================================
        # 10. WEBSITE
        # ====================================================================

        if options.get("web", True):

            website = data.get("website")

            if website is not None and not website.empty:

                pdf.add_page()

                pdf.section_title(
                    "10",
                    "สถิติการสมัครสมาชิกเว็บไซต์ www.thaieasypass.com"
                )

                required = [
                    "month_label",
                    "new_registrations",
                    "cumulative_total",
                ]

                if all(c in website.columns for c in required):

                    # ---------- Chart: dual-axis (ใช้ chart_line + bar แยกเป็น 2 รูป) ----------
                    # fig 1: สมัครใหม่รายเดือน
                    fig_path = chart_line(
                        website["month_label"].tolist(),
                        [website["new_registrations"].tolist()],
                        ["สมัครใหม่/เดือน"],
                        "จำนวนการสมัครสมาชิกใหม่รายเดือนบนเว็บไซต์ thaieasypass",
                        ylabel="บัญชี",
                        color_list=["#2E7D32"],
                    )
                    temp_files.append(fig_path)
                    pdf.image_block(fig_path, w=178)

                    # fig 2: สะสม
                    fig_path2 = chart_line(
                        website["month_label"].tolist(),
                        [website["cumulative_total"].tolist()],
                        ["สมาชิกสะสม"],
                        "จำนวนการสมัครสมาชิกสะสมบนเว็บไซต์ thaieasypass",
                        ylabel="บัญชี",
                        color_list=["#D32F2F"],
                    )
                    temp_files.append(fig_path2)
                    pdf.image_block(fig_path2, w=178)

                    # ---------- Table ----------
                    headers = [
                        "เดือน",
                        "สมัครใหม่ (บัญชี)",
                        "สะสม (บัญชี)",
                    ]

                    rows = [
                        [
                            r["month_label"],
                            _fmt_number(r["new_registrations"]),
                            _fmt_number(r["cumulative_total"]),
                        ]
                        for _, r in website.iterrows()
                    ]

                    pdf.simple_table(
                        headers,
                        rows,
                        col_widths=[50, 68, 68],
                        font_size=8.5,
                        highlight_last=True,
                    )

        # ====================================================================
        # 11. CARD STATUS
        # ====================================================================

        if options.get("status", True):

            card_status = data.get(
                "card_status"
            )

            card_detail = data.get(
                "card_detail"
            )

            inactive_bal = data.get(
                "inactive_bal"
            )

            if (
                card_status is not None
                and not card_status.empty
            ):

                pdf.add_page()

                pdf.section_title(
                    "11",
                    "สถานะบัตร Easy Pass ในระบบ CCH"
                )

                required = [
                    "month_label",
                    "active_cards",
                    "suspended_cards",
                    "low_balance_cards",
                    "lost_count"
                ]

                if all(
                    c in card_status.columns
                    for c in required
                ):

                    fig_path = chart_line(
                        card_status["month_label"].tolist(),
                        [
                            card_status["active_cards"].tolist(),
                            card_status["suspended_cards"].tolist(),
                            card_status["low_balance_cards"].tolist(),
                            card_status["lost_count"].tolist()
                        ],
                        [
                            "Active",
                            "Suspended",
                            "Low Balance",
                            "Lost"
                        ],
                        "สถานะบัตรรายเดือน ปีงบประมาณ 2569",
                        ylabel="จำนวนบัตร"
                    )

                    temp_files.append(
                        fig_path
                    )

                    pdf.image_block(
                        fig_path,
                        w=178
                    )

            if (
                card_detail is not None
                and not card_detail.empty
            ):

                pdf.sub_title(
                    "รายละเอียดสถานะบัตรอัตโนมัติ Easy Pass ในระบบ CCH"
                )

                headers = [
                    "กลุ่มสถานะ",
                    "สถานะ",
                    "BEM",
                    "EXAT",
                    "รวม (บัตร)",
                    "%"
                ]

                rows = [
                    [
                        r.get(
                            "status_group",
                            ""
                        ),
                        r.get(
                            "status_name",
                            ""
                        ),
                        _fmt_number(
                            r.get(
                                "bem_count",
                                0
                            )
                        ),
                        _fmt_number(
                            r.get(
                                "exat_count",
                                0
                            )
                        ),
                        _fmt_number(
                            r.get(
                                "total_count",
                                0
                            )
                        ),
                        _fmt_percent(
                            r.get(
                                "percent",
                                0
                            )
                        )
                    ]
                    for _, r in card_detail.iterrows()
                ]

                pdf.simple_table(
                    headers,
                    rows,
                    col_widths=[
                        35,
                        55,
                        22,
                        35,
                        28,
                        15
                    ],
                    font_size=7.5
                )

            if (
                inactive_bal is not None
                and not inactive_bal.empty
            ):

                pdf.ln(3)

                pdf.sub_title(
                    "เงินคงเหลือในบัตรพร้อมใช้งานไม่เคลื่อนไหวเกิน 2 ปี"
                )

                headers = [
                    "ช่วงจำนวนเงิน",
                    "จำนวนบัตร",
                    "จำนวนเงิน (บาท)"
                ]

                rows = [
                    [
                        r.get(
                            "amount_range",
                            ""
                        ),
                        _fmt_number(
                            r.get(
                                "card_count",
                                0
                            )
                        ),
                        _fmt_baht(
                            r.get(
                                "amount_baht",
                                0
                            )
                        )
                    ]
                    for _, r in inactive_bal.iterrows()
                ]

                pdf.simple_table(
                    headers,
                    rows,
                    col_widths=[
                        60,
                        60,
                        70
                    ],
                    font_size=8,
                    highlight_last=True
                )


        # ====================================================================
        # 12. CUSTOMER SERVICE
        # ====================================================================

        if options.get("cs", True):

            cs = data.get(
                "cs"
            )

            if (
                cs is not None
                and not cs.empty
            ):

                pdf.add_page()

                pdf.section_title(
                    "12",
                    "ศูนย์บริการลูกค้า (Easy Pass Customer Service)"
                )

                if all(
                    c in cs.columns
                    for c in [
                        "month_label",
                        "total_cases"
                    ]
                ):

                    fig_path = chart_line(
                        cs["month_label"].tolist(),
                        [
                            cs["total_cases"].tolist()
                        ],
                        [
                            "เรื่องร้องเรียนรวม"
                        ],
                        "สถิติการรับเรื่องร้องเรียน ปีงบประมาณ 2569",
                        ylabel="เรื่อง",
                        color_list=[
                            "#0B5ED7"
                        ]
                    )

                    temp_files.append(
                        fig_path
                    )

                    pdf.image_block(
                        fig_path,
                        w=178
                    )

                base_cols = [
                    "month_label",
                    "total_cases"
                ]

                extra_cols = [
                    c
                    for c in cs.columns
                    if c not in [
                        "month",
                        "month_label",
                        "total_cases"
                    ]
                ]

                show_cols = (
                    base_cols +
                    extra_cols[:6]
                )

                headers = [
                    {
                        "month_label": "เดือน",
                        "total_cases": "รวม"
                    }.get(
                        c,
                        c
                    )
                    for c in show_cols
                ]

                rows = []

                for _, r in cs.iterrows():

                    row = []

                    for c in show_cols:

                        v = r[c]

                        if isinstance(
                            v,
                            (int, float)
                        ):

                            row.append(
                                f"{v:,.0f}"
                            )

                        else:

                            row.append(
                                str(v)
                            )

                    rows.append(row)

                widths = (
                    [22] +
                    [28] *
                    (
                        len(headers) -
                        1
                    )
                )

                pdf.simple_table(
                    headers,
                    rows,
                    col_widths=widths,
                    font_size=7.5
                )


        # ====================================================================
        # 13. ANNUAL SUMMARY
        # ====================================================================

        if options.get(
            "annual",
            True
        ):

            annual = data.get(
                "annual_summary"
            )

            if (
                annual is not None
                and not annual.empty
            ):

                pdf.add_page()

                pdf.section_title(
                    "13",
                    "สรุปยอดสะสมปีงบประมาณ 2569"
                )

                headers = [
                    "หมวด",
                    "ตัวชี้วัด",
                    "ค่า",
                    "หน่วย"
                ]

                rows = []

                for _, r in annual.iterrows():

                    v = r.get(
                        "value",
                        0
                    )

                    unit = r.get(
                        "unit",
                        ""
                    )

                    if (
                        unit == "บาท"
                        and _safe_float(v) >= 1e9
                    ):

                        val_str = (
                            f"{_safe_float(v) / 1e9:,.2f} พันล้าน"
                        )

                    elif unit == "บาท":

                        val_str = _fmt_baht(v)

                    else:

                        val_str = _fmt_number(v)

                    rows.append([
                        r.get(
                            "category",
                            ""
                        ),
                        r.get(
                            "metric_th",
                            ""
                        ),
                        val_str,
                        unit
                    ])

                pdf.simple_table(
                    headers,
                    rows,
                    col_widths=[
                        35,
                        95,
                        35,
                        25
                    ],
                    font_size=8
                )


        # ====================================================================
        # 14. NOTES
        # ====================================================================

        pdf.add_page()

        pdf.section_title(
            "14",
            "หมายเหตุและแหล่งข้อมูล"
        )

        notes = [

            "1. ข้อมูลในรายงานนี้รวบรวมจากระบบรายงานปริมาณจราจร/รายได้ และฐานข้อมูล CCH (Data Warehouse)",

            "2. ตัวเลขบางส่วนยังไม่ผ่านการตรวจสอบจาก กตร. ฝก. และอาจมีการปรับปรุงภายหลัง",

            "3. เกณฑ์ Early Warning ถูกจัดเก็บถาวรบนดิสก์ และสามารถปรับได้ที่เมนูตั้งค่าของผู้ดูแลระบบ",

            "4. รายงานนี้เป็นเอกสารลับเฉพาะสำหรับผู้บริหารและผู้ที่ได้รับอนุญาตเท่านั้น",

            "5. ข้อมูลรายเดือนอ้างอิงตามปีงบประมาณ 2569 (ต.ค. 2568 - ก.ย. 2569)",
        ]

        pdf.set_font(
            f,
            "",
            9
        )

        pdf.set_text_color(
            50,
            50,
            50
        )

        for note_text in notes:

            pdf.multi_cell(
                0,
                5.5,
                note_text
            )

            pdf.ln(0.5)

        pdf.ln(8)

        pdf.set_font(
            f,
            "I",
            8
        )

        pdf.set_text_color(
            130,
            130,
            130
        )

        pdf.cell(
            0,
            5,
            "— จบรายงาน —",
            0,
            1,
            "C"
        )

    finally:

        # --------------------------------------------------------------------
        # Delete temporary PNG files
        # --------------------------------------------------------------------

        for tf in temp_files:

            try:

                Path(tf).unlink(
                    missing_ok=True
                )

            except Exception:
                pass

    # =========================================================================
    # OUTPUT
    # =========================================================================

    try:

        # fpdf2
        output = pdf.output(
            dest="S"
        )

        if isinstance(
            output,
            bytes
        ):

            return output

        if isinstance(
            output,
            bytearray
        ):

            return bytes(output)

        if isinstance(
            output,
            str
        ):

            return output.encode(
                "latin1",
                errors="ignore"
            )

        return bytes(output)

    except TypeError:

        # fallback สำหรับ fpdf version อื่น
        output = pdf.output(
            dest="S"
        )

        if isinstance(
            output,
            bytes
        ):
            return output

        return bytes(
            output,
            "latin1"
        )