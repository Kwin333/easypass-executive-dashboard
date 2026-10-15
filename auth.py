"""
auth.py
============================================================
EASY PASS Executive Dashboard
ระบบยืนยันตัวตนและจัดการสิทธิ์ (RBAC)
การทางพิเศษแห่งประเทศไทย (กทพ.)

รองรับ 4 ระดับสิทธิ์:
    admin
    governor
    executive
    viewer

Authentication:
    - YAML
    - bcrypt
    - Streamlit Session State
    - Audit Log

Login UI:
    - EXAT Executive Corporate Style
    - Centered Logo (Base64 inline image)
    - High Resolution Logo Rendering
    - Responsive Layout
============================================================
"""

from pathlib import Path
import base64
import datetime
from io import BytesIO

import bcrypt
import pandas as pd
import streamlit as st
import yaml
from PIL import Image, ImageOps


# ============================================================
# PATH CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

CONFIG_DIR = BASE_DIR / "config"
ASSETS_DIR = BASE_DIR / "assets"
LOG_DIR = BASE_DIR / "logs"

CONFIG_PATH = CONFIG_DIR / "users.yaml"
LOG_PATH = LOG_DIR / "audit_log.csv"
LOGO_PATH = ASSETS_DIR / "exat_logo.png"


# ============================================================
# ROLE CONFIGURATION
# ============================================================

ROLE_LABELS = {
    "admin": "ผู้ดูแลระบบ",
    "governor": "ผู้ว่าการ กทพ.",
    "executive": "ผู้บริหาร",
    "viewer": "เจ้าหน้าที่",
}

VALID_ROLES = {
    "admin",
    "governor",
    "executive",
    "viewer",
}


# ============================================================
# LOAD USERS
# ============================================================

def _load_users():

    if not CONFIG_PATH.exists():

        st.error(
            "ไม่พบไฟล์ users.yaml\n\n"
            f"ระบบกำลังค้นหาไฟล์:\n{CONFIG_PATH}"
        )

        st.stop()

    try:

        with open(
            CONFIG_PATH,
            "r",
            encoding="utf-8",
        ) as file:

            data = yaml.safe_load(file) or {}

        users = data.get(
            "users",
            {},
        )

        if not isinstance(
            users,
            dict,
        ):

            st.error(
                "รูปแบบ users.yaml ไม่ถูกต้อง\n"
                "ข้อมูล users ต้องเป็น dictionary"
            )

            st.stop()

        return users

    except yaml.YAMLError as error:

        st.error(
            "ไม่สามารถอ่าน users.yaml ได้\n\n"
            f"รายละเอียด: {error}"
        )

        st.stop()

    except Exception as error:

        st.error(
            "เกิดข้อผิดพลาดในการโหลด users.yaml\n\n"
            f"รายละเอียด: {error}"
        )

        st.stop()


# ============================================================
# LOAD LOGO
# ============================================================

def _load_logo():

    if not LOGO_PATH.exists():

        return None

    try:

        image = Image.open(
            LOGO_PATH
        )

        # โหลดข้อมูลภาพเข้าสู่ Memory
        image.load()

        # ป้องกันปัญหา EXIF orientation
        try:

            image = ImageOps.exif_transpose(
                image
            )

        except Exception:

            pass

        # แปลงโหมดภาพให้เหมาะสม
        if image.mode not in (
            "RGB",
            "RGBA",
        ):

            if "A" in image.getbands():

                image = image.convert(
                    "RGBA"
                )

            else:

                image = image.convert(
                    "RGB"
                )

        return image

    except Exception:

        return None


# ============================================================
# LOGO → BASE64 (สำหรับแสดงผลแบบ inline HTML)
# ============================================================

def _logo_to_base64(image):
    """
    แปลง PIL Image เป็น base64 PNG

    หมายเหตุ:
        - ไม่ทำ resize ที่นี่
        - ปล่อยขนาด native ให้ CSS จัดการด้วย max-width/max-height
        - เพื่อคงความคมชัดสูงสุด
    """

    if image is None:

        return None

    try:

        buffer = BytesIO()

        image.save(
            buffer,
            format="PNG",
            optimize=True,
        )

        return base64.b64encode(
            buffer.getvalue()
        ).decode("utf-8")

    except Exception:

        return None


# ============================================================
# AUDIT LOG
# ============================================================

def _log_event(
    username,
    name,
    role,
    status,
):

    try:

        LOG_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        now = datetime.datetime.now()

        row = pd.DataFrame(
            [
                {
                    "timestamp": now.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    "username": username,
                    "name": name,
                    "role": role,
                    "role_label": ROLE_LABELS.get(
                        role,
                        role,
                    ),
                    "status": status,
                }
            ]
        )

        if LOG_PATH.exists():

            row.to_csv(
                LOG_PATH,
                mode="a",
                header=False,
                index=False,
                encoding="utf-8-sig",
            )

        else:

            row.to_csv(
                LOG_PATH,
                mode="w",
                header=True,
                index=False,
                encoding="utf-8-sig",
            )

    except Exception:

        # Audit log ไม่ควรทำให้ Login ล้ม
        pass


# ============================================================
# GET AUDIT LOG
# ============================================================

def get_audit_log():

    if not LOG_PATH.exists():

        return None

    try:

        return pd.read_csv(
            LOG_PATH,
            encoding="utf-8-sig",
        )

    except Exception:

        return None


# ============================================================
# LOGOUT
# ============================================================

def logout():

    for key in (
        "auth_ok",
        "username",
        "name",
        "role",
    ):

        st.session_state.pop(
            key,
            None,
        )

    st.rerun()


# ============================================================
# LOGIN PAGE CSS
# ============================================================

def _apply_login_style():

    st.markdown(
        """
        <style>

        /* ==================================================
           GLOBAL BACKGROUND
        ================================================== */

        [data-testid="stAppViewContainer"] {

            background:
                linear-gradient(
                    135deg,
                    #03142F 0%,
                    #082B55 48%,
                    #0757A6 100%
                ) !important;
        }


        [data-testid="stHeader"] {

            background:
                transparent !important;
        }


        [data-testid="stToolbar"] {

            visibility:
                hidden !important;
        }


        /* ==================================================
           MAIN PAGE
        ================================================== */

        .main .block-container {

            max-width:
                1180px !important;

            padding-top:
                25px !important;

            padding-bottom:
                35px !important;

            padding-left:
                25px !important;

            padding-right:
                25px !important;
        }


        /* ==================================================
           LOGO CONTAINER
        ================================================== */

        .exat-logo-wrapper {

            width:
                100% !important;

            display:
                flex !important;

            flex-direction:
                column !important;

            justify-content:
                center !important;

            align-items:
                center !important;

            text-align:
                center !important;

            margin:
                0 auto 18px auto !important;

            padding:
                0 !important;
        }


        .exat-logo-wrapper img {

            display:
                block !important;

            /* สำคัญ: ปล่อยให้สัดส่วนจริง ไม่บังคับ height ตายตัว */
            width:
                auto !important;

            height:
                auto !important;

            max-width:
                320px !important;

            max-height:
                220px !important;

            object-fit:
                contain !important;

            object-position:
                center center !important;

            margin:
                0 auto !important;

            padding:
                0 !important;

            border:
                none !important;

            /* เพิ่มความคมชัดเมื่อย่อ */
            image-rendering:
                -webkit-optimize-contrast;

            image-rendering:
                crisp-edges;
        }


        /* ==================================================
           LOGIN TITLE
        ================================================== */

        .exat-login-title {

            color:
                #FFFFFF !important;

            text-align:
                center !important;

            font-size:
                30px !important;

            font-weight:
                800 !important;

            line-height:
                1.3 !important;

            margin:
                0 0 6px 0 !important;

            padding:
                0 !important;

            letter-spacing:
                0.1px !important;

            text-shadow:
                0 2px 8px
                rgba(0, 0, 0, 0.25) !important;
        }


        /* ==================================================
           ORGANIZATION
        ================================================== */

        .exat-login-org {

            color:
                #FFFFFF !important;

            text-align:
                center !important;

            font-size:
                16px !important;

            font-weight:
                600 !important;

            line-height:
                1.4 !important;

            margin:
                0 0 3px 0 !important;

            padding:
                0 !important;
        }


        /* ==================================================
           DESCRIPTION
        ================================================== */

        .exat-login-description {

            color:
                #DCEBFF !important;

            text-align:
                center !important;

            font-size:
                13px !important;

            line-height:
                1.5 !important;

            margin:
                0 0 28px 0 !important;

            padding:
                0 !important;
        }


        /* ==================================================
           LOGIN CARD AREA
        ================================================== */

        .login-card-container {

            width:
                100% !important;

            display:
                flex !important;

            justify-content:
                center !important;

            align-items:
                center !important;

            margin:
                0 auto !important;
        }


        /* ==================================================
           FORM
        ================================================== */

        [data-testid="stForm"] {

            background:
                #FFFFFF !important;

            border:
                1px solid #E2E8F0 !important;

            border-radius:
                14px !important;

            padding:
                30px 32px 28px 32px !important;

            box-shadow:
                0 24px 65px
                rgba(0, 0, 0, 0.30) !important;
        }


        /* ==================================================
           FORM TITLE
        ================================================== */

        .exat-form-title {

            color:
                #0A315D !important;

            text-align:
                center !important;

            font-size:
                22px !important;

            font-weight:
                750 !important;

            line-height:
                1.4 !important;

            margin:
                0 0 4px 0 !important;

            padding:
                0 !important;
        }


        /* ==================================================
           FORM DESCRIPTION
        ================================================== */

        .exat-form-description {

            color:
                #64748B !important;

            text-align:
                center !important;

            font-size:
                13px !important;

            line-height:
                1.5 !important;

            margin:
                0 0 22px 0 !important;

            padding:
                0 !important;
        }


        /* ==================================================
           LABEL
        ================================================== */

        [data-testid="stForm"] label {

            color:
                #334155 !important;

            font-size:
                13px !important;

            font-weight:
                600 !important;
        }


        [data-testid="stForm"] label p {

            color:
                #334155 !important;
        }


        /* ==================================================
           INPUT CONTAINER (Username & Password Match 100%)
        ================================================== */

        /* Outer container for both Username and Password inputs */
        [data-testid="stForm"] .stTextInput > div > div {
            background: #F8FAFC !important;
            border: 1.5px solid #CBD5E1 !important;
            border-radius: 10px !important;
            min-height: 46px !important;
            width: 100% !important;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04) !important;
            transition: all 0.2s ease-in-out !important;
            overflow: hidden !important;
        }

        [data-testid="stForm"] .stTextInput > div > div:hover {
            border-color: #94A3B8 !important;
            background: #FFFFFF !important;
        }

        [data-testid="stForm"] .stTextInput > div > div:focus-within {
            border-color: #0B5ED7 !important;
            background: #FFFFFF !important;
            box-shadow: 0 0 0 3.5px rgba(11, 94, 215, 0.15) !important;
        }

        /* Strip all inner borders and backgrounds (eliminates double-border in password field) */
        [data-testid="stForm"] .stTextInput > div > div div {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }

        [data-testid="stForm"] .stTextInput input {
            color: #0F172A !important;
            background: transparent !important;
            border: none !important;
            font-size: 14.5px !important;
            font-weight: 500 !important;
            padding: 10px 14px !important;
            box-shadow: none !important;
            outline: none !important;
            height: 44px !important;
        }

        [data-testid="stForm"] .stTextInput input::placeholder {
            color: #94A3B8 !important;
            opacity: 1 !important;
        }

        /* Password visibility toggle button */
        [data-testid="stForm"] .stTextInput button,
        [data-testid="stForm"] .stTextInput button:hover,
        [data-testid="stForm"] .stTextInput button:focus,
        [data-testid="stForm"] .stTextInput button:active {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            width: 44px !important;
            min-width: 44px !important;
            max-width: 44px !important;
            height: 100% !important;
            min-height: 40px !important;
            margin: 0 !important;
            padding: 0 8px !important;
            color: #64748B !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            cursor: pointer !important;
            border-radius: 0 !important;
        }

        [data-testid="stForm"] .stTextInput button svg {
            fill: #64748B !important;
            width: 18px !important;
            height: 18px !important;
            transition: fill 0.2s ease !important;
        }

        [data-testid="stForm"] .stTextInput button:hover svg {
            fill: #0B5ED7 !important;
        }

        /* ==================================================
           SUBMIT BUTTON (ONLY target the actual submit button)
        ================================================== */

        [data-testid="stFormSubmitButton"] button,
        [data-testid="stForm"] .stButton > button {
            width: 100% !important;
            min-height: 48px !important;
            margin-top: 14px !important;
            background: linear-gradient(135deg, #0B5ED7 0%, #003366 100%) !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 10px !important;
            font-size: 16px !important;
            font-weight: 700 !important;
            letter-spacing: 0.3px !important;
            box-shadow: 0 4px 14px rgba(11, 94, 215, 0.32) !important;
            transition: all 0.25s ease-in-out !important;
            cursor: pointer !important;
        }

        [data-testid="stFormSubmitButton"] button:hover,
        [data-testid="stForm"] .stButton > button:hover {
            background: linear-gradient(135deg, #084298 0%, #002244 100%) !important;
            box-shadow: 0 6px 20px rgba(11, 94, 215, 0.45) !important;
            transform: translateY(-1px) !important;
        }

        [data-testid="stFormSubmitButton"] button:active,
        [data-testid="stForm"] .stButton > button:active {
            transform: translateY(0px) !important;
            box-shadow: 0 2px 8px rgba(11, 94, 215, 0.3) !important;
        }

        [data-testid="stFormSubmitButton"] button p,
        [data-testid="stFormSubmitButton"] button span,
        [data-testid="stForm"] .stButton > button p,
        [data-testid="stForm"] .stButton > button span {
            color: #FFFFFF !important;
            font-weight: 700 !important;
            font-size: 15.5px !important;
        }


        /* ==================================================
           FOOTER
        ================================================== */

        .exat-login-footer {

            color:
                rgba(255, 255, 255, 0.82) !important;

            text-align:
                center !important;

            font-size:
                11px !important;

            line-height:
                1.8 !important;

            margin:
                23px 0 0 0 !important;

            padding:
                0 !important;
        }


        /* ==================================================
           MOBILE
        ================================================== */

        @media (max-width: 640px) {

            .main .block-container {

                padding-left:
                    18px !important;

                padding-right:
                    18px !important;

                padding-top:
                    20px !important;
            }


            .exat-logo-wrapper img {

                max-height:
                    160px !important;

                max-width:
                    220px !important;
            }


            .exat-login-title {

                font-size:
                    23px !important;
            }


            .exat-login-org {

                font-size:
                    14px !important;
            }


            [data-testid="stForm"] {

                padding:
                    24px 20px !important;
            }
        }

        </style>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# REQUIRE LOGIN
# ============================================================

def require_login():

    # ========================================================
    # ALREADY LOGIN
    # ========================================================

    if st.session_state.get(
        "auth_ok",
        False,
    ):

        return {
            "username": st.session_state.get(
                "username",
                "",
            ),
            "name": st.session_state.get(
                "name",
                "",
            ),
            "role": st.session_state.get(
                "role",
                "viewer",
            ),
        }


    # ========================================================
    # LOAD USERS
    # ========================================================

    users = _load_users()


    # ========================================================
    # STYLE
    # ========================================================

    _apply_login_style()


    # ========================================================
    # LOGO
    #
    # ใช้ base64 inline <img> แทน st.image()
    # เพื่อ:
    #   1. จัดกึ่งกลางได้จริง (อยู่ใน flex container เดียวกัน)
    #   2. คุมสัดส่วนภาพด้วย CSS ได้ 100%
    #   3. คงความคมชัดตาม native resolution
    # ========================================================

    logo = _load_logo()

    logo_b64 = _logo_to_base64(
        logo
    )

    if logo_b64:

        st.markdown(
            f"""
            <div class="exat-logo-wrapper">
                <img src="data:image/png;base64,{logo_b64}"
                     alt="EXAT Logo" />
            </div>
            """,
            unsafe_allow_html=True,
        )


    # ========================================================
    # TITLE
    # ========================================================

    st.markdown(
        """
        <div class="exat-login-title">
            EASY PASS Executive Dashboard
        </div>
        """,
        unsafe_allow_html=True,
    )


    # ========================================================
    # ORGANIZATION
    # ========================================================

    st.markdown(
        """
        <div class="exat-login-org">
            การทางพิเศษแห่งประเทศไทย (กทพ.)
        </div>
        """,
        unsafe_allow_html=True,
    )


    # ========================================================
    # DESCRIPTION
    # ========================================================

    st.markdown(
        """
        <div class="exat-login-description">
            Executive Intelligence &amp; Analytics
        </div>
        """,
        unsafe_allow_html=True,
    )


    # ========================================================
    # LOGIN CARD
    # ========================================================

    left_space, login_column, right_space = st.columns(
        [1, 1.15, 1]
    )


    with login_column:

        with st.form(
            "login_form",
            clear_on_submit=False,
        ):

            # ------------------------------------------------
            # FORM TITLE
            # ------------------------------------------------

            st.markdown(
                """
                <div class="exat-form-title">
                    เข้าสู่ระบบ
                </div>
                """,
                unsafe_allow_html=True,
            )


            # ------------------------------------------------
            # FORM DESCRIPTION
            # ------------------------------------------------

            st.markdown(
                """
                <div class="exat-form-description">
                    กรุณาระบุข้อมูลผู้ใช้งาน
                </div>
                """,
                unsafe_allow_html=True,
            )


            # ------------------------------------------------
            # USERNAME
            # ------------------------------------------------

            username = st.text_input(
                "ชื่อผู้ใช้งาน",
                placeholder="Username",
            )


            # ------------------------------------------------
            # PASSWORD
            # ------------------------------------------------

            password = st.text_input(
                "รหัสผ่าน",
                placeholder="Password",
                type="password",
            )


            # ------------------------------------------------
            # LOGIN BUTTON
            # ------------------------------------------------

            submitted = st.form_submit_button("เข้าสู่ระบบ")


        # ====================================================
        # AUTHENTICATION
        # ====================================================

        if submitted:

            username = username.strip()

            user_record = users.get(
                username
            )

            login_success = False


            # ------------------------------------------------
            # CHECK USER
            # ------------------------------------------------

            if isinstance(
                user_record,
                dict,
            ):

                password_hash = user_record.get(
                    "password_hash",
                    "",
                )

                if password_hash:

                    try:

                        login_success = bcrypt.checkpw(
                            password.encode("utf-8"),
                            password_hash.encode("utf-8"),
                        )

                    except Exception:

                        login_success = False


            # =================================================
            # SUCCESS
            # =================================================

            if login_success:

                role = user_record.get(
                    "role",
                    "viewer",
                )

                name = user_record.get(
                    "name",
                    username,
                )


                if role not in VALID_ROLES:

                    role = "viewer"


                # ------------------------------------------------
                # SESSION
                # ------------------------------------------------

                st.session_state["auth_ok"] = True

                st.session_state["username"] = (
                    username
                )

                st.session_state["name"] = (
                    name
                )

                st.session_state["role"] = (
                    role
                )


                # ------------------------------------------------
                # AUDIT
                # ------------------------------------------------

                _log_event(
                    username=username,
                    name=name,
                    role=role,
                    status="login_success",
                )


                # ------------------------------------------------
                # RERUN
                # ------------------------------------------------

                st.rerun()


            # =================================================
            # FAILED
            # =================================================

            else:

                _log_event(
                    username=username,
                    name="",
                    role="unknown",
                    status="login_failed",
                )

                st.error(
                    "ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง"
                )


    # ========================================================
    # FOOTER
    # ========================================================

    st.markdown(
        """
        <div class="exat-login-footer">
            EASY PASS Executive Dashboard
            <br>
            ระบบสารสนเทศเพื่อสนับสนุนการวิเคราะห์
            และการตัดสินใจเชิงบริหาร
            <br>
            การทางพิเศษแห่งประเทศไทย (กทพ.)
        </div>
        """,
        unsafe_allow_html=True,
    )


    # ========================================================
    # STOP
    # ========================================================

    st.stop()