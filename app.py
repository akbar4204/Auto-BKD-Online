import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# --- KONFIGURASI ---
# ⚠️ PENTING: PASTIKAN ID INI TETAP MENGGUNAKAN ID SHARED DRIVE ANDA
DRIVE_FOLDER_ID = '0AC6nzjQVEw17Uk9PVA' 
SHEET_NAME = 'Database_BKD'

# Setup Scope
scope = ['https://www.googleapis.com/auth/spreadsheets',
         'https://www.googleapis.com/auth/drive']

# --- LOGIKA KONEKSI (HYBRID) ---
try:
    if "gcp_service_account" in st.secrets:
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    else:
        creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
    
    client = gspread.authorize(creds)
    drive_service = build('drive', 'v3', credentials=creds)

except Exception as e:
    st.error(f"Gagal koneksi: {e}")
    st.stop()

# --- FUNGSI-FUNGSI ---
def get_or_create_folder(folder_name, parent_id):
    query = f"name='{folder_name}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = drive_service.files().list(q=query, fields="files(id)", supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
    files = results.get('files', [])
    if files:
        return files[0]['id']
    else:
        metadata = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [parent_id]}
        folder = drive_service.files().create(body=metadata, fields='id', supportsAllDrives=True).execute()
        return folder.get('id')

def upload_to_drive(file_obj, filename, category_name):
    folder_kategori_id = get_or_create_folder(category_name, DRIVE_FOLDER_ID)
    file_metadata = {'name': filename, 'parents': [folder_kategori_id]}
    media = MediaIoBaseUpload(file_obj, mimetype=file_obj.type)
    file = drive_service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink', supportsAllDrives=True).execute()
    return file.get('webViewLink')

def update_sheet(data_list):
    sheet = client.open(SHEET_NAME).sheet1
    existing = sheet.get_all_values()
    if not existing:
        sheet.append_row(["Nama Dosen", "Tanggal", "Nama File", "Kategori", "Link Bukti"])
    sheet.append_row(data_list)

def get_all_data():
    """Mengambil semua data dari Google Sheet untuk ditampilkan"""
    try:
        sheet = client.open(SHEET_NAME).sheet1
        data = sheet.get_all_records()
        return data
    except Exception as e:
        return []

# --- TAMPILAN WEBSITE ---
st.set_page_config(page_title="Auto-BKD V2", page_icon="🗂️", layout="wide")
st.title("🗂️ Sistem Manajemen BKD")

# Buat 2 Tab Menu
tab1, tab2 = st.tabs(["📤 Upload Baru", "📂 Arsip File"])

# === TAB 1: FORM UPLOAD ===
with tab1:
    st.header("Upload Bukti Kegiatan")
    st.info("File akan otomatis masuk ke Folder Kategori di Google Drive.")
    
    with st.form("upload_form"):
        col1, col2 = st.columns(2)
        with col1:
            nama_dosen = st.text_input("Nama Dosen")
            # 👇 UPDATE DI SINI: Menambahkan "Berkas Lain"
            kategori = st.selectbox("Kategori", ["Pendidikan", "Penelitian", "Pengabdian", "Penunjang", "Berkas Lain"])
        with col2:
            tanggal = st.date_input("Tanggal Kegiatan")
            nama_kegiatan = st.text_input("Nama Kegiatan")
            
        uploaded_file = st.file_uploader("File Bukti (PDF/Gambar)", type=['pdf', 'jpg', 'png', 'docx'])
        
        submit = st.form_submit_button("Arsipkan Sekarang")

    if submit and nama_dosen and uploaded_file and nama_kegiatan:
        with st.spinner('Sedang memproses...'):
            try:
                nama_file_final = f"[{nama_dosen}] {nama_kegiatan}"
                link = upload_to_drive(uploaded_file, nama_file_final, kategori)
                update_sheet([nama_dosen, str(tanggal), nama_kegiatan, kategori, link])
                st.success(f"✅ Sukses! Data tersimpan di kategori **{kategori}**.")
            except Exception as e:
                st.error(f"Error: {e}")

# === TAB 2: ARSIP DATA ===
with tab2:
    st.header("🗃️ Database Arsip")
    
    if st.button("🔄 Refresh Data"):
        st.rerun()
        
    data_bkd = get_all_data()
    
    if data_bkd:
        search = st.text_input("🔍 Cari data (Ketik nama dosen atau kegiatan):")
        st.dataframe(
            data_bkd, 
            use_container_width=True,
            column_config={
                "Link Bukti": st.column_config.LinkColumn("Bukti Fisik", display_text="Buka File"),
                "Tanggal": st.column_config.DateColumn("Tanggal", format="DD/MM/YYYY")
            }
        )
        st.caption(f"Total Dokumen: {len(data_bkd)}")
    else:
        st.warning("Belum ada data yang tersimpan.")

# === WATERMARK / FOOTER ===
footer="""<style>
.footer {
    position: fixed;
    left: 0;
    bottom: 0;
    width: 100%;
    background-color: #f0f2f6;
    color: #555;
    text-align: center;
    padding: 10px;
    font-size: 14px;
    font-weight: bold;
    z-index: 100;
}
</style>
<div class="footer">
<p>Created by Akbar Rizqi Kurniawan | Auto-BKD System © 2026</p>
</div>
"""
st.markdown(footer, unsafe_allow_html=True)
