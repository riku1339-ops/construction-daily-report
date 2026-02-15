import streamlit as st
from io import BytesIO
from datetime import date as dt_date

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

import google.auth
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload


# ====== 設定（ここだけ自分の値に）======
FOLDER_ID = "11PdWOkAKQjqvxEiDsGQGSMP_xQQVndYw?usp=drive_link"  # 共有したいDriveフォルダID
DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.file"


def make_pdf(data: dict) -> BytesIO:
    """PDFを作ってBytesIOで返す（ここでは保存しない）"""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica", 10)
    y = height - 50

    lines = [
        f"【日付】 {data['date']}",
        f"【現場名】 {data['site']}",
        f"【天候】 {data['weather']}",
        f"【記入者】 {data['manager']}",
        f"【作業員】 {data['workers']}",
        "",
        "【安全確認（KY・指差呼称・保護具など）】",
        data["safety"],
        "",
        "【作業内容（工程・数量・進捗）】",
        data["work"],
        "",
        "【指摘・是正・課題（あれば）】",
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

            # ざっくり幅制限（長すぎると切る）
            c.drawString(40, y, sub[:110])
            y -= 14
        y -= 6

    c.save()
    buf.seek(0)
    return buf


def upload_pdf_to_drive(pdf_buffer: BytesIO, filename: str) -> dict:
    """Driveにアップロードして、作成したファイル情報を返す"""
    credentials, _ = google.auth.default(scopes=[DRIVE_SCOPE])
    drive_service = build("drive", "v3", credentials=credentials)

    # 念のため先頭に戻す
    pdf_buffer.seek(0)

    file_metadata = {
        "name": filename,
        "parents": [FOLDER_ID],
    }

    media = MediaIoBaseUpload(pdf_buffer, mimetype="application/pdf", resumable=True)

    uploaded = (
        drive_service.files()
        .create(
            body=file_metadata,
            media_body=media,
            fields="id, webViewLink",
        )
        .execute()
    )
    return uploaded


# ====== UI ======
st.title("📋 施工管理 日報（Streamlit）")

with st.form("daily_report"):
    col1, col2 = st.columns(2)

    with col1:
        date_val = st.date_input("日付", value=dt_date.today())
        site = st.text_input("現場名")
        weather = st.text_input("天候（例：晴れ/曇り/雨）")

    with col2:
        manager = st.text_input("記入者")
        workers = st.text_input("作業員（例：5名）")
        safety = st.text_area("安全確認（KY・指差呼称・保護具など）", height=80)

    work = st.text_area("作業内容（工程・数量・進捗）", height=120)
    issues = st.text_area("指摘・是正・課題（あれば）", height=80)
    tomorrow = st.text_area("明日の予定", height=80)

    save_to_drive = st.checkbox("Google Driveにも保存する", value=True)

    submitted = st.form_submit_button("PDFを生成")


if submitted:
    data = {
        "date": date_val.strftime("%Y-%m-%d"),
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
    filename = f"施工管理日報_{data['date']}.pdf"

    # ① まずダウンロードは必ず出す
    st.download_button(
        label="PDFをダウンロード",
        data=pdf_buffer.getvalue(),
        file_name=filename,
        mime="application/pdf",
    )
    st.success("PDFが正常に生成されました！")

    # ② Drive保存（チェックONのときだけ）
    if save_to_drive:
        try:
            # uploadでseek(0)するので、ここは何もしなくてOK
            uploaded = upload_pdf_to_drive(pdf_buffer, filename)
            st.success(f"Driveに保存しました！ fileId={uploaded['id']}")
            if uploaded.get("webViewLink"):
                st.markdown(f"[Driveで開く]({uploaded['webViewLink']})")
        except Exception as e:
            st.error(f"Drive保存でエラー: {e}")
            st.info(
                "※対策: (1) Drive APIを有効化 (2) 保存先フォルダをCloud Runのサービスアカウントに共有 "
                "(3) requirements.txtに google-api-python-client を入れる"
            )
