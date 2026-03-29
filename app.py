import streamlit as st
import ee
import geemap
import json

# 1. Konfigurasi Halaman Web
st.set_page_config(
    layout="wide", 
    page_title="Marine Plastic Tracker"
)

# 2. Fungsi untuk autentikasi Earth Engine
@st.cache_resource
def initialize_ee():
    """Inisialisasi Google Earth Engine menggunakan Secrets"""
    try:
        if 'GCP_SERVICE_ACCOUNT_KEY' in st.secrets:
            secret_input = st.secrets['GCP_SERVICE_ACCOUNT_KEY']
            info = json.loads(secret_input)
            credentials = ee.ServiceAccountCredentials(info['client_email'], key_data=info['private_key'])
            ee.Initialize(credentials)
            return True
        else:
            ee.Initialize()
            return True
    except Exception as e:
        st.error(f"Error initializing Earth Engine: {str(e)}")
        return False

# 3. Jalankan Inisialisasi
ee_initialized = initialize_ee()

# 4. Header Aplikasi
st.title("🌊 Marine Plastic Tracker")
st.markdown("---")

if ee_initialized:
    # 5. Sidebar untuk kontrol
    with st.sidebar:
        st.header("⚙️ Kontrol")
        basemap_choice = st.selectbox(
            "Pilih Peta Dasar", 
            ["Satellite", "Roadmap", "Terrain", "Hybrid"]
        )
        data_type = st.selectbox(
            "Pilih Jenis Data", 
            ["Marine Debris", "SST", "Chlorophyll"]
        )
        if st.button("🔄 Refresh Peta"):
            st.rerun()

    # 6. Layout utama
    col1, col2 = st.columns([3, 1])

    with col1:
        st.subheader(f"🗺️ Peta: {data_type}")
        try:
            # Inisialisasi Peta
            m = geemap.Map(center=[-6.12, 106.83], zoom=10)
            
            # Tambahkan Basemap
            if basemap_choice == "Satellite":
                m.add_basemap('SATELLITE')
            elif basemap_choice == "Roadmap":
                m.add_basemap('ROADMAP')
            elif basemap_choice == "Terrain":
                m.add_basemap('TERRAIN')
            else:
                m.add_basemap('HYBRID')

            # --- LOGIKA LAYER DATA ---
            if data_type == "Marine Debris":
                s2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED") \
                    .filterDate('2024-01-01', '2024-12-31') \
                    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10)) \
                    .median()
                
                # Floating Debris Index (FDI)
                fdi = s2.expression('B8 - (B6 + (B8 - B6) * 0.5)', {
                    'B8': s2.select('B8'),
                    'B6': s2.select('B6')
                }).rename('FDI')
                
                m.add_layer(s2, {'bands': ['B4', 'B3', 'B2'], 'max': 3000}, 'Citra Satelit')
                m.add_layer(fdi, {'min': 0, 'max': 1000, 'palette': ['white', 'orange', 'red']}, 'Potensi Sampah (FDI)')

            elif data_type == "SST":
                sst = ee.ImageCollection('NASA/OCEANDATA/MODIS-Aqua/L3SMI') \
                    .filterDate('2024-01-01', '2024-12-31') \
                    .select('sst').mean()
                m.add_layer(sst, {'min': 15, 'max': 35, 'palette': ['blue', 'cyan', 'yellow', 'red']}, 'SST')
            
            elif data_type == "Chlorophyll":
                chl = ee.ImageCollection('NASA/OCEANDATA/MODIS-Aqua/L3SMI') \
                    .filterDate('2024-01-01', '2024-12-31') \
                    .select('chlor_a').mean()
                m.add_layer(chl, {'min': 0, 'max': 30, 'palette': ['purple', 'blue', 'green', 'yellow']}, 'Chlorophyll')

            # Tampilkan ke Streamlit
            m.to_streamlit(height=600)

        except Exception as e:
            st.error(f"Gagal menampilkan peta: {e}")

    with col2:
        st.subheader("📊 Informasi")
        st.info("""
        **Indikator:**
        - **Marine Debris:** Menggunakan FDI (Floating Debris Index).
        - **SST:** Suhu permukaan laut (°C).
        - **Chlorophyll:** Konsentrasi klorofil-a.
        """)
        st.metric("Status GEE", "Aktif")

else:
    st.error("❌ Gagal terhubung ke Google Earth Engine.")
    st.info("Pastikan Secrets di Dashboard Streamlit sudah terisi dengan benar.")
