# BARIS AJAIB: Memperbaiki error pkg_resources secara paksa
import sys
import subprocess

try:
    import pkg_resources
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "setuptools"])
    import pkg_resources

import streamlit as st
import ee
import geemap.foliumap as geemap
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
            return True
        else:
            ee.Initialize()
            return True
    except Exception as e:
        st.error(f"GEE Error: {e}")
        return False

ee_status = init_gee()

# --- 3. TAMPILAN ---
st.title("🌊 Marine Plastic Tracker")
st.markdown("---")

if ee_status:
    with st.sidebar:
        st.header("⚙️ Kontrol")
        data_type = st.selectbox("Pilih Data", ["Marine Debris", "SST", "Chlorophyll"])
        if st.button("🔄 Refresh"):
            st.rerun()

    col1, col2 = st.columns([3, 1])

    with col1:
        try:
            m = geemap.Map(center=[-6.12, 106.83], zoom=10)
            m.add_basemap('SATELLITE')
            
            if data_type == "Marine Debris":
                # Dataset Sentinel-2
                s2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED") \
                    .filterDate('2024-01-01', '2024-12-31') \
                    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10)) \
                    .median()
                m.add_layer(s2, {'bands': ['B4', 'B3', 'B2'], 'max': 3000}, 'Citra Satelit')
            
            m.to_streamlit(height=600)
        except Exception as e:
            st.error(f"Gagal memuat peta: {e}")

    with col2:
        st.subheader("📊 Info")
        st.metric("Status GEE", "Aktif")
        st.write("Aplikasi monitoring sampah plastik laut.")

else:
    st.error("Koneksi GEE Gagal. Cek Secrets!")
