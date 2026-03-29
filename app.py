import streamlit as st
import ee
import geemap.foliumap as geemap # Menggunakan versi folium agar lebih ringan
import json

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(layout="wide", page_title="Marine Plastic Tracker")

# --- 2. LOGIN GEE (DIBUAT SEDERHANA) ---
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
    
    # Buat Peta Sederhana
    m = geemap.Map(center=[-6.12, 106.83], zoom=10)
    m.add_basemap('SATELLITE')
    
    # Tampilkan Peta
    m.to_streamlit(height=600)
else:
    st.error(f"Gagal Login GEE: {pesan}")
