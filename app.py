import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# --- KONFIGURASI ---
# GANTI DENGAN ID SHARED DRIVE ANDA
DRIVE_FOLDER_ID = '0AC6nzjQVEw17Uk9PVA' 
SHEET_NAME = 'Database_BKD'

# Setup Scope
scope = ['https://www.googleapis.com/auth/spreadsheets',
         'https://www.googleapis.com/auth/drive']

# --- LOGIKA KONEKSI (HYBRID: FILE vs SECRETS) ---
try:
    # Prioritas 1: Cek apakah ada Secrets (Untuk Streamlit Cloud)
    if "gcp_service_account" in st.secrets:
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    # Prioritas 2: Cek file lokal (Untuk di Laptop sendiri)
    else:
        creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
    
    # Bangun service
    client = gspread.authorize(creds)
    drive_service = build('drive', 'v3', credentials=creds)

except Exception as e:
    st.error(f"Gagal koneksi: {e}")
    st.stop()

# --- FUNGSI CARI/BUAT FOLDER ---
def get_or_create_folder(folder_name, parent_id):
    query = f"name='{folder_name}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = drive_service.files().list(q=query, fields="files(id)", supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
    files = results.get('files', [])

    if files:
        return files[0]['id']
    else:
        metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id]
        }
        folder = drive_service.files().create(body=metadata, fields='id', supportsAllDrives=True).execute()
        return folder.get('id')

# --- FUNGSI UPLOAD ---
def upload_to_drive(file_obj, filename, category_name):
    folder_kategori_id = get_or_create_folder(category_name, DRIVE_FOLDER_ID)
    
    file_metadata = {'name': filename, 'parents': [folder_kategori_id]}
    media = MediaIoBaseUpload(file_obj, mimetype=file_obj.type)
    
    file = drive_service.files().create(
        body=file_metadata, 
        media_body=media, 
        fields='id, webViewLink',
        supportsAllDrives=True
    ).execute()
    return file.get('webViewLink')

def update_sheet(data_list):
    sheet = client.open(SHEET_NAME).sheet1
    existing = sheet.get_all_values()
    if not existing:
        sheet.append_row(["Nama Dosen", "Tanggal", "Nama File", "Kategori", "Link Bukti"])
    sheet.append_row(data_list)

# --- TAMPILAN WEBSITE ---
st.set_page_config(page_title="Auto-BKD Cloud", page_icon="☁️")
st.title("☁️ Auto-BKD (Online Version)")
st.markdown("Sistem Portofolio Dosen - Terhubung ke Google Drive Kampus")

with st.form("upload_form"):
    nama_dosen = st.text_input("Nama Dosen")
    uploaded_file = st.file_uploader("File Bukti", type=['pdf', 'jpg', 'png', 'docx'])
    nama_kegiatan = st.text_input("Nama Kegiatan")
    kategori = st.selectbox("Pilih Folder Kategori", ["Pendidikan", "Penelitian", "Pengabdian", "Penunjang"])
    tanggal = st.date_input("Tanggal")
    
    submit = st.form_submit_button("Arsipkan ke Cloud")

if submit and nama_dosen and uploaded_file and nama_kegiatan:
    with st.spinner('Sedang memproses ke server...'):
        try:
            nama_file_final = f"[{nama_dosen}] {nama_kegiatan}"
            link = upload_to_drive(uploaded_file, nama_file_final, kategori)
            update_sheet([nama_dosen, str(tanggal), nama_kegiatan, kategori, link])
            st.success(f"✅ Sukses! Data tersimpan.")
        except Exception as e:
            st.error(f"Error: {e}")