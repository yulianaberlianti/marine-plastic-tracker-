# SKRIP UTAMA (Web Streamlit)
import streamlit as st
import ee
import geemap 
import json

# 1. Konfigurasi Halaman Web
st.set_page_config(
    layout="wide", 
    page_title="Marine Plastic Tracker"
)

# 2. Fungsi untuk autentikasi Earth Engine (PENTING UNTUK DEPLOY)
@st.cache_resource
def initialize_ee():
    """Inisialisasi Google Earth Engine menggunakan Secrets"""
    try:
        # Cek apakah kunci ada di Secrets
        if 'GCP_SERVICE_ACCOUNT_KEY' in st.secrets:
            secret_input = st.secrets['GCP_SERVICE_ACCOUNT_KEY']
            info = json.loads(secret_input)
            credentials = ee.ServiceAccountCredentials(info['client_email'], key_data=info['private_key'])
            ee.Initialize(credentials)
            return True
        else:
            # Fallback untuk lokal (jika sudah login di laptop)
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
        
        basemap = st.selectbox(
            "Pilih Peta Dasar",
            ["Satellite", "Roadmap", "Terrain", "Hybrid"]
        )
        
        data_type = st.selectbox(
            "Pilih Jenis Data",
            ["Marine Debris (Sentinel-2)", "Sea Surface Temperature", "Chlorophyll"]
        )
        
        if st.button("🔄 Refresh Peta"):
            st.rerun()
    
    # 6. Layout utama
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader(f"🗺️ Peta: {data_type}")
        
        try:
            # Inisialisasi Peta (Default Jakarta Bay)
           m = geemap.Map(center=[-6.12, 106.83], zoom=10, add_google_map=False)
            
            # Tambahkan peta dasar (Pastikan sejajar dengan inisialisasi m)
            if basemap == "Satellite":
                m.add_basemap('SATELLITE')
            elif basemap == "Roadmap":
                m.add_basemap('ROADMAP')
            elif basemap == "Terrain":
                m.add_basemap('TERRAIN')
            else:
                m.add_basemap('HYBRID')
            
            # --- LOGIKA DATA ---
            if data_type == "Marine Debris (Sentinel-2)":
                # Menggunakan Floating Debris Index (FDI) Sederhana
                s2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED") \
                    .filterDate('2024-01-01', '2024-12-31') \
                    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10)) \
                    .median()
                
                # Rumus FDI: NIR - (RE2 + (NIR - RE2) * 0.5)
                fdi = s2.expression('B8 - (B6 + (B8 - B6) * 0.5)', {
                    'B8': s2.select('B8'),
                    'B6': s2.select('B6')
                }).rename('FDI')
                
                m.add_layer(s2, {'bands': ['B4', 'B3', 'B2'], 'max': 3000}, 'Citra Asli')
                m.add_layer(fdi, {'min': 0, 'max': 1000, 'palette': ['white', 'orange', 'red']}, 'Potensi Sampah (FDI)')

            elif data_type == "Sea Surface Temperature":
                sst = ee.ImageCollection('NASA/OCEANDATA/MODIS-Aqua/L3SMI') \
                    .filterDate('2024-01-01', '2024-12-31') \
                    .select('sst').mean()
                m.add_layer(sst, {'min': 15, 'max': 35, 'palette': ['blue', 'cyan', 'yellow', 'red']}, 'SST')
            
            elif data_type == "Chlorophyll":
                chl = ee.ImageCollection('NASA/OCEANDATA/MODIS-Aqua/L3SMI') \
                    .filterDate('2024-01-01', '2024-12-31') \
                    .select('chlor_a').mean()
                m.add_layer(chl, {'min': 0, 'max': 30, 'palette': ['purple', 'blue', 'green', 'yellow']}, 'Chlorophyll')

            # Tampilkan peta
            m.to_streamlit(height=600)
            
        except Exception as e:
            st.error(f"Error creating map: {str(e)}")

    with col2:
        st.subheader("📊 Informasi")
        st.info("""
        **Tentang Aplikasi:**
        Aplikasi ini memonitor kondisi laut menggunakan data satelit Google Earth Engine.
        
        **Indikator:**
        - **FDI (Floating Debris Index):** Mendeteksi benda mengapung (termasuk plastik) di permukaan air.
        - **SST:** Suhu permukaan laut.
        - **Chlorophyll:** Konsentrasi klorofil (kesehatan ekosistem).
        """)
        
        st.metric("Status GEE", "Active")
        st.metric("Satelit Utama", "Sentinel-2 / MODIS")

else:
    st.error("❌ Google Earth Engine tidak dapat diinisialisasi")
    st.markdown("""
    ### Cara Memperbaiki:
    1. Pastikan isi **Secrets** di Streamlit Cloud sudah benar (format JSON).
    2. Pastikan akun email Service Account sudah diberi izin (*role*) **Earth Engine Resource Viewer** di Google Cloud Console.
    """)
