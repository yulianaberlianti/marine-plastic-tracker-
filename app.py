import streamlit as st
import ee
import folium
from streamlit_folium import st_folium
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
        # Buat peta Folium
        m = folium.Map(location=[-6.12, 106.83], zoom_start=10)

        # Ambil tile URL Sentinel-2 dari Earth Engine
        s2 = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterDate('2024-01-01', '2024-12-31')
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10))
            .median()
        )

        vis_params = {'bands': ['B4', 'B3', 'B2'], 'max': 3000}
        map_id = s2.getMapId(vis_params)
        tile_url = map_id['tile_fetcher'].url_format

        # Tambahkan tile GEE ke peta Folium
        folium.TileLayer(
            tiles=tile_url,
            attr='Google Earth Engine',
            name='Sentinel-2 RGB',
            overlay=True,
            control=True
        ).add_to(m)

        folium.LayerControl().add_to(m)

        # Tampilkan ke Streamlit
        st_folium(m, width="100%", height=600)

    except Exception as e:
        st.error(f"Error pada Peta: {e}")
else:
    st.error(f"Gagal Login GEE: {pesan}")
