# SKRIP UTAMA (Web Streamlit)
import streamlit as st
import ee
import geemap
import traceback

# 1. Konfigurasi Halaman Web
st.set_page_config(
    layout="wide", 
    page_title="Marine Plastic Tracker"
)

# 2. Header Aplikasi
st.title("🌊 Marine Plastic Tracker")
st.markdown("---")

# 3. Fungsi untuk autentikasi Earth Engine
@st.cache_resource
def initialize_ee():
    """Inisialisasi Google Earth Engine"""
    try:
        # Coba autentikasi dengan service account atau anonymous
        ee.Initialize()
        return True
    except Exception as e:
        try:
            # Alternatif untuk development
            ee.Initialize(opt_url='https://earthengine-highvolume.googleapis.com')
            return True
        except:
            st.error(f"Error initializing Earth Engine: {str(e)}")
            st.info("Pastikan Anda sudah login ke Google Earth Engine")
            return False

# 4. Inisialisasi Earth Engine
ee_initialized = initialize_ee()

if ee_initialized:
    # 5. Sidebar untuk kontrol
    with st.sidebar:
        st.header("⚙️ Kontrol")
        
        # Pilihan peta dasar
        basemap = st.selectbox(
            "Pilih Peta Dasar",
            ["Satellite", "Roadmap", "Terrain", "Hybrid"]
        )
        
        # Pilihan jenis data
        data_type = st.selectbox(
            "Pilih Jenis Data",
            ["Marine Debris", "Sea Surface Temperature", "Chlorophyll"]
        )
        
        # Tombol refresh
        if st.button("🔄 Refresh Peta"):
            st.rerun()
    
    # 6. Layout utama dengan dua kolom
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("🗺️ Peta Deteksi Sampah Plastik")
        
        # Buat peta interaktif
        try:
            m = geemap.Map(center=[0, 150], zoom=3)
            
            # Tambahkan peta dasar berdasarkan pilihan
            if basemap == "Satellite":
                m.add_basemap('SATELLITE')
            elif basemap == "Roadmap":
                m.add_basemap('ROADMAP')
            elif basemap == "Terrain":
                m.add_basemap('TERRAIN')
            else:
                m.add_basemap('HYBRID')
            
            # Contoh: Tambahkan data sampah laut (gunakan dataset yang sesuai)
            if data_type == "Marine Debris":
                st.info("Menampilkan data marine debris...")
                # Contoh dataset: Tambahkan kode untuk data marine debris
                # Anda bisa menambahkan layer dari Earth Engine di sini
                
            elif data_type == "Sea Surface Temperature":
                st.info("Menampilkan data suhu permukaan laut...")
                # Dataset contoh: NASA/USGS Landsat
                try:
                    # Dataset suhu permukaan laut
                    sst = ee.ImageCollection('NASA/OCEANDATA/MODIS-Aqua/L3SMI') \
                        .filterDate('2024-01-01', '2024-12-31') \
                        .select('sst') \
                        .mean()
                    
                    vis_params = {
                        'min': 0,
                        'max': 30,
                        'palette': ['blue', 'cyan', 'green', 'yellow', 'red']
                    }
                    m.add_layer(sst, vis_params, 'Sea Surface Temperature')
                except Exception as e:
                    st.warning(f"Tidak dapat memuat data SST: {str(e)}")
            
            elif data_type == "Chlorophyll":
                st.info("Menampilkan data klorofil...")
                try:
                    # Dataset klorofil
                    chl = ee.ImageCollection('NASA/OCEANDATA/MODIS-Aqua/L3SMI') \
                        .filterDate('2024-01-01', '2024-12-31') \
                        .select('chlor_a') \
                        .mean()
                    
                    vis_params = {
                        'min': 0,
                        'max': 50,
                        'palette': ['purple', 'blue', 'green', 'yellow']
                    }
                    m.add_layer(chl, vis_params, 'Chlorophyll Concentration')
                except Exception as e:
                    st.warning(f"Tidak dapat memuat data klorofil: {str(e)}")
            
            # Tampilkan peta
            m.to_streamlit(height=600)
            
        except Exception as e:
            st.error(f"Error creating map: {str(e)}")
            st.code(traceback.format_exc())
    
    with col2:
        st.subheader("📊 Informasi")
        
        # Informasi lokasi
        st.info("""
        **Tentang Aplikasi:**
        Aplikasi ini memonitor sampah plastik di laut menggunakan data satelit.
        
        **Data yang Ditampilkan:**
        - Marine debris distribution
        - Sea surface temperature
        - Chlorophyll concentration
        """)
        
        # Statistik sederhana
        st.metric("Status", "Active" if ee_initialized else "Error")
        st.metric("Data Source", "Google Earth Engine")
        
        # Catatan
        st.warning("""
        **Catatan:**
        - Data ditampilkan berdasarkan koleksi dataset dari Earth Engine
        - Beberapa dataset mungkin memerlukan autentikasi tambahan
        """)
else:
    # 7. Tampilkan pesan error jika Earth Engine tidak bisa diinisialisasi
    st.error("❌ Google Earth Engine tidak dapat diinisialisasi")
    st.markdown("""
    ### Cara Memperbaiki:
    
    1. **Login ke Google Earth Engine**:
       ```bash
       earthengine authenticate
