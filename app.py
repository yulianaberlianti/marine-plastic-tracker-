import streamlit as st
import ee
import geemap.foliumap as geemap
import json

# --- KONFIGURASI HALAMAN ---
st.set_page_config(layout="wide", page_title="Marine Plastic Tracker")

# --- INISIALISASI EARTH ENGINE (SINGLETON PATTERN) ---
@st.cache_resource # Ini kuncinya! Supaya inisialisasi cuma jalan 1x saja
def init_ee():
    if 'GCP_SERVICE_ACCOUNT_KEY' in st.secrets:
        try:
            # Mengambil string JSON dari Secrets
            secret_input = st.secrets['GCP_SERVICE_ACCOUNT_KEY']
            info = json.loads(secret_input)
            
            # Autentikasi menggunakan Service Account
            credentials = ee.ServiceAccountCredentials(info['client_email'], key_data=info['private_key'])
            ee.Initialize(credentials)
            return True
        except Exception as e:
            st.error(f"Gagal Inisialisasi GEE: {e}")
            return False
    else:
        st.error("Kunci 'GCP_SERVICE_ACCOUNT_KEY' tidak ditemukan di Streamlit Secrets!")
        return False

# Jalankan inisialisasi
ee_initialized = init_ee()

# --- TAMPILAN WEB ---
st.title("🌊 Marine Plastic Debris Detector")

if ee_initialized:
    # Buat peta sederhana dulu untuk tes
    m = geemap.Map(center=[-7.84, 110.43], zoom=12) # Contoh koordinat DIY/Piyungan
    m.add_basemap('SATELLITE')
    
    # Tampilkan di Streamlit
    m.to_streamlit(height=600)
else:
    st.warning("Silakan periksa konfigurasi Secrets kamu di dashboard Streamlit.")
