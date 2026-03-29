import streamlit as st
import ee
import geemap
import json

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(layout="wide", page_title="Marine Plastic Tracker")

# --- 2. LOGIN GEE ---
@st.cache_resource
def init_gee():
    try:
        if 'GCP_SERVICE_ACCOUNT_KEY' in st.secrets:
            info = json.loads(st.secrets['GCP_SERVICE_ACCOUNT_KEY'])
            credentials = ee.ServiceAccountCredentials(info['client_email'], key_data=info['private_key'])
            ee.Initialize(credentials)
            return True, "Sukses"
        return False, "Secrets tidak ditemukan"
    except Exception as e:
        return False, str(e)

status, pesan = init_gee()

# --- 3. TAMPILAN ---
st.title("🌊 Marine Plastic Tracker")

if status:
    st.success("Koneksi Earth Engine Berhasil!")
    
    try:
        # Gunakan geemap.Map() standar, bukan foliumap
        # add_google_map=False untuk menghindari error API Key
        m = geemap.Map(center=[-6.12, 106.83], zoom=10, add_google_map=False)
        
        # Tambahkan layer Sentinel-2 sederhana sebagai tes
        s2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED") \
            .filterDate('2024-01-01', '2024-12-31') \
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10)) \
            .median()
        
        m.add_layer(s2, {'bands': ['B4', 'B3', 'B2'], 'max': 3000}, 'Sentinel-2 RGB')
        
        # Tampilkan ke Streamlit
        m.to_streamlit(height=600)
        
    except Exception as e:
        st.error(f"Error pada Peta: {e}")
        st.info("Tips: Jika error 'Box', pastikan requirements.txt sudah diupdate ke python-box==6.1.0")
else:
    st.error(f"Gagal Login GEE: {pesan}")
