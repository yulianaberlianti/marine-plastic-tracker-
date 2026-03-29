# SKRIP UTAMA (Web Streamlit)
import streamlit as st
import ee
import geemap.foliumap as geemap # Pakai foliumap khusus untuk web
import json

# Inisialisasi GEE
if 'GCP_SERVICE_ACCOUNT_KEY' in st.secrets:
    try:
        # Load kunci dari Secrets
        info = json.loads(st.secrets['GCP_SERVICE_ACCOUNT_KEY'])
        credentials = ee.ServiceAccountCredentials(info['client_email'], key_data=info['private_key'])
        
        # Inisialisasi hanya jika belum ada
        if not ee.data._credentials:
            ee.Initialize(credentials)
    except Exception as e:
        st.error(f"Gagal Inisialisasi: {e}")
else:
    st.error("Kunci Secrets tidak ditemukan!")

# 1. Konfigurasi Halaman Web
st.set_page_config(layout="wide", page_title="Marine Plastic Tracker")
st.title("🌊 Marine Plastic Debris Detector (Sentinel-2)")
st.write("Aplikasi ini mendeteksi potensi sampah plastik di pesisir menggunakan satelit dan AI.")

# 2. Inisialisasi Earth Engine
# (Penting: Untuk deploy web, gunakan Service Account)
try:
    ee.Initialize()
except:
    ee.Authenticate()
    ee.Initialize()

# 3. Sidebar untuk Input Pengguna
st.sidebar.header("Pengaturan Area")
location = st.sidebar.text_input("Cari Lokasi (misal: Jakarta Bay)", "Jakarta Bay")

# 4. Fungsi Deteksi Plastik (Floating Debris Index)
def detect_plastic(image):
    # Rumus FDI sederhana untuk Sentinel-2
    # NIR - (RE2 + (NIR - RE2) * 10.0)
    fdi = image.expression(
        'NIR - (RE2 + (NIR - RE2) * 0.5)', {
            'NIR': image.select('B8'),
            'RE2': image.select('B6')
        }).rename('FDI')
    return fdi

# 5. Ambil Data Sentinel-2
s2 = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
      .filterDate('2024-01-01', '2025-12-31')
      .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10))
      .median())

fdi_result = detect_plastic(s2)

# 6. Tampilkan Peta
m = geemap.Map()
m.add_basemap('SATELLITE')
m.addLayer(s2, {'bands': ['B4', 'B3', 'B2'], 'max': 3000}, 'Citra Asli')
m.addLayer(fdi_result, {'min': 0, 'max': 1000, 'palette': ['white', 'red']}, 'Potensi Sampah (FDI)')

m.to_streamlit(height=600)

st.info("💡 Warna merah pada peta menunjukkan area dengan reflektansi tinggi yang berpotensi sebagai sampah plastik mengapung.")

