import streamlit as st
from zoneinfo import ZoneInfo
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import re

JST = ZoneInfo("Asia/Tokyo")

st.set_page_config(page_title="施工管理 日報", layout="centered")

st.title("📋 施工管理 日報（Streamlit）")

# ---- 入力フォーム ----
with st.form("daily_report"):
    col1, col2 = st.columns(2)
    with col1:
        date = st.date_input("日付", value=datetime.now(JST).date())
        site = st.text_input("現場名")
        weather = st.text_input("天候（例：晴れ/曇り/雨）")
    with col2:
        manager = st.text_input("記入者")
        workers = st.text_input("作業員（例：5名）")
        safety = st.text_area("安全確認（KY・指差呼称・保護具など）", height=80)

    work = st.text_area("作業内容（工程・数量・進捗）", height=140)
    issues = st.text_area("指摘・是正・課題（あれば）", height=100)
    tomorrow = st.text_area("明日の予定", height=100)

    submitted = st.form_submit_button("PDFを生成")

# ---- PDF生成 ----
def make_pdf(data: dict) -> BytesIO:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    y = height - 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, "施工管理 日報")
    y -= 30

    c.setFont("Helvetica", 10)

    lines = [
        f"日付: {data['date']}",
        f"現場名: {data['site']}",
        f"天候: {data['weather']}",
        f"記入者: {data['manager']}",
        f"作業員: {data['workers']}",
        "",
        "【作業内容】",
        data["work"],
        "",
        "【安全確認】",
        data["safety"],
        "",
        "【指摘・是正・課題】",
        data["issues"],
        "",
        "【明日の予定】",
        data["tomorrow"],
    ]

    for line in lines:
        # 改行が多い文章を安全に分割
        for sub in str(line).split("\n"):

            if y < 60:
                c.showPage()
                c.setFont("Helvetica", 10)
                y = height - 50
            c.drawString(40, y, sub[:110])  # ざっくり幅制限
            y -= 14
        y -= 6

    c.save()
    buf.seek(0)
    return buf

if submitted:
    data = {
        "date": date.strftime("%Y-%m-%d"),
        "site": site,
        "weather": weather,
        "manager": manager,
        "workers": workers,
        "safety": safety,
        "work": work,
        "issues": issues,
        "tomorrow": tomorrow,
    }
    pdf_buffer = make_pdf(data)
    # ---- Driveへ保存 ----
    import google.auth
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload
    
    FOLDER_ID = "11PdWOkAKQjqvxEiDsGQGSMP_xQQVndYw"

    credentials, project = google.auth.default(
        scopes=["https://www.googleapis.com/auth/drive.file"]
    )

    drive_service = build("drive", "v3", credentials=credentials)

    file_metadata = {
        "name": f"日報_{data['date']}.pdf",
        "parents": [FOLDER_ID]
    }

    pdf_buffer.seek(0)

    media = MediaIoBaseUpload(pdf_buffer, mimetype="application/pdf")

    drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()

    st.success("Driveに保存しました！")

    st.download_button(
        label="PDFをダウンロード",
        data=pdf_buffer,
        file_name=f"日報_{data['date']}.pdf",
        mime="application/pdf",
    )

    st.success("PDFが生成されました！")
