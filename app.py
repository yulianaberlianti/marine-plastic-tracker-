import streamlit as st
import ee
import folium
from streamlit_folium import st_folium
import json
import pandas as pd
import plotly.express as px
from datetime import date

# ─────────────────────────────────────────────
# 1. KONFIGURASI HALAMAN
# ─────────────────────────────────────────────
st.set_page_config(
    layout="wide",
    page_title="🌊 Marine Plastic Tracker",
    page_icon="🌊"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
    .main-header {
        background: linear-gradient(135deg, #0a3d62 0%, #1e6f9f 50%, #0a9396 100%);
        padding: 2rem 2.5rem; border-radius: 16px; color: white; margin-bottom: 1.5rem;
    }
    .main-header h1 { font-family: 'Syne', sans-serif; font-size: 2.4rem; margin: 0; font-weight: 800; }
    .main-header p  { font-size: 1rem; margin: 0.5rem 0 0; opacity: 0.85; }
    .metric-card {
        background: linear-gradient(135deg, #0a3d62, #1e6f9f);
        border-radius: 12px; padding: 1.2rem; color: white; text-align: center;
        border: 1px solid rgba(255,255,255,0.15);
    }
    .metric-card .val { font-family:'Syne',sans-serif; font-size: 2rem; font-weight: 700; }
    .metric-card .lbl { font-size: 0.78rem; opacity: 0.8; margin-top: 4px; }
    .info-box {
        background: #f0f9ff; border-left: 4px solid #0a9396;
        border-radius: 8px; padding: 1rem 1.2rem; margin: 0.6rem 0;
    }
    .stButton>button {
        background: linear-gradient(135deg, #0a3d62, #0a9396);
        color: white; border: none; border-radius: 8px;
        padding: 0.6rem 2rem; font-weight: 600; width: 100%; font-size: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 2. DATA HOTSPOT SAMPAH
# ─────────────────────────────────────────────
HOTSPOTS = {
    "Teluk Jakarta": [
        {"name": "Muara Ciliwung",           "lat": -6.117, "lon": 106.835, "level": "Kritis",
         "info": "Sungai Ciliwung membawa ±150 ton sampah/hari ke laut"},
        {"name": "Muara Angke",              "lat": -6.102, "lon": 106.741, "level": "Kritis",
         "info": "Kawasan nelayan dengan akumulasi plastik tinggi"},
        {"name": "Kepulauan Seribu (Sel.)",  "lat": -5.850, "lon": 106.650, "level": "Sedang",
         "info": "Arus membawa sampah dari daratan ke kepulauan"},
        {"name": "Muara Bekasi",             "lat": -6.090, "lon": 107.000, "level": "Tinggi",
         "info": "Kawasan industri dengan limbah plastik tinggi"},
    ],
    "Pesisir Jawa Barat": [
        {"name": "Muara Citarum",  "lat": -6.016, "lon": 107.489, "level": "Kritis",
         "info": "Citarum pernah disebut sungai terkotor di dunia"},
        {"name": "Pantai Eretan", "lat": -6.250, "lon": 108.220, "level": "Tinggi",
         "info": "Akumulasi sampah dari arus laut Jawa"},
    ],
    "Pesisir Jawa Tengah": [
        {"name": "Muara Serayu",   "lat": -7.740, "lon": 109.010, "level": "Sedang",
         "info": "DAS Serayu membawa material dari pegunungan"},
        {"name": "Semarang Utara", "lat": -6.940, "lon": 110.430, "level": "Tinggi",
         "info": "Kawasan pelabuhan dengan polusi plastik"},
    ],
    "Pesisir Jawa Timur": [
        {"name": "Muara Brantas (Surabaya)", "lat": -7.190, "lon": 112.730, "level": "Kritis",
         "info": "Brantas salah satu DAS paling tercemar plastik"},
        {"name": "Selat Madura",            "lat": -7.120, "lon": 112.850, "level": "Tinggi",
         "info": "Arus sempit mengkonsentrasikan sampah plastik"},
    ],
    "Kalimantan Selatan": [
        {"name": "Muara Barito (Banjarmasin)", "lat": -3.320, "lon": 114.590, "level": "Tinggi",
         "info": "Kota sungai dengan banyak aktivitas di atas air"},
    ],
    "Sulawesi Selatan": [
        {"name": "Teluk Makassar", "lat": -5.130, "lon": 119.410, "level": "Tinggi",
         "info": "Kota besar dengan pengelolaan sampah yang masih kurang"},
    ],
}

AREA_COORDS = {
    "Teluk Jakarta":       {"lat": -6.05,  "lon": 106.83, "zoom": 11},
    "Pesisir Jawa Barat":  {"lat": -6.20,  "lon": 107.80, "zoom": 9},
    "Pesisir Jawa Tengah": {"lat": -6.90,  "lon": 110.20, "zoom": 9},
    "Pesisir Jawa Timur":  {"lat": -7.20,  "lon": 112.70, "zoom": 9},
    "Kalimantan Selatan":  {"lat": -3.40,  "lon": 114.60, "zoom": 9},
    "Sulawesi Selatan":    {"lat": -5.10,  "lon": 119.40, "zoom": 9},
    "Seluruh Indonesia":   {"lat": -2.50,  "lon": 118.00, "zoom": 5},
}

LEVEL_COLOR = {"Kritis": "#e63946", "Tinggi": "#f4a261", "Sedang": "#2a9d8f"}

# ─────────────────────────────────────────────
# 3. LOGIN GEE
# ─────────────────────────────────────────────
@st.cache_resource
def init_gee():
    try:
        if 'GCP_SERVICE_ACCOUNT_KEY' in st.secrets:
            info  = json.loads(st.secrets['GCP_SERVICE_ACCOUNT_KEY'])
            creds = ee.ServiceAccountCredentials(info['client_email'], key_data=info['private_key'])
            ee.Initialize(creds)
            return True, "OK"
        return False, "Secret tidak ditemukan"
    except Exception as e:
        return False, str(e)

gee_ok, gee_msg = init_gee()

# ─────────────────────────────────────────────
# 4. HEADER
# ─────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🌊 Marine Plastic Tracker</h1>
    <p>Deteksi sampah plastik laut berbasis Satelit Sentinel-2 &amp; Google Earth Engine · Indonesia</p>
</div>
""", unsafe_allow_html=True)

if not gee_ok:
    st.error(f"❌ Gagal Login GEE: {gee_msg}")
    st.stop()

st.success("✅ Koneksi Google Earth Engine berhasil!")

# ─────────────────────────────────────────────
# 5. SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🗂️ Pengaturan Analisis")
    st.markdown("---")

    area_pilihan = st.selectbox("📍 Pilih Area", list(AREA_COORDS.keys()))

    st.markdown("### 📅 Rentang Tanggal")
    col1, col2 = st.columns(2)
    with col1:
        tgl_mulai = st.date_input("Mulai", value=date(2024, 1, 1),
                                   min_value=date(2019, 1, 1), max_value=date(2025, 12, 31))
    with col2:
        tgl_akhir = st.date_input("Akhir", value=date(2024, 12, 31),
                                   min_value=date(2019, 1, 1), max_value=date(2025, 12, 31))

    tutupan_awan = st.slider("☁️ Maks. Tutupan Awan (%)", 0, 50, 10)

    st.markdown("### 🗺️ Layer Peta")
    tampil_rgb    = st.checkbox("🛰️ Citra Asli (RGB)",       value=True)
    tampil_fdi    = st.checkbox("🔴 Deteksi Plastik (FDI)",  value=True)
    tampil_marker = st.checkbox("📍 Hotspot Sampah",          value=True)

    st.markdown("---")
    st.markdown("""
    <div style='font-size:0.75rem;opacity:0.75;line-height:1.7'>
    <b>Tentang FDI</b><br>
    Floating Debris Index mendeteksi material mengapung berdasarkan
    reflektansi band NIR Sentinel-2.<br><br>
    <b>Sumber:</b><br>
    · Sentinel-2 SR (ESA/Copernicus)<br>
    · Biermann et al. (2020)<br>
    · BRIN Marine Database
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 6. TABS
# ─────────────────────────────────────────────
tab_peta, tab_stat, tab_info = st.tabs(["🗺️ Peta Analisis", "📊 Statistik", "ℹ️ Tentang Metode"])

# ══ TAB PETA ══════════════════════════════════
with tab_peta:
    coord = AREA_COORDS[area_pilihan]
    spots = HOTSPOTS.get(area_pilihan, [s for v in HOTSPOTS.values() for s in v])

    m = folium.Map(location=[coord["lat"], coord["lon"]],
                   zoom_start=coord["zoom"],
                   tiles="CartoDB dark_matter")

    # Layer RGB
    if tampil_rgb:
        try:
            s2_rgb = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                      .filterDate(str(tgl_mulai), str(tgl_akhir))
                      .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', tutupan_awan))
                      .median())
            rgb_id = s2_rgb.getMapId({'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000, 'gamma': 1.4})
            folium.TileLayer(
                tiles=rgb_id['tile_fetcher'].url_format,
                attr='Sentinel-2 RGB | ESA/GEE',
                name='🛰️ Citra Asli (RGB)',
                overlay=True, control=True
            ).add_to(m)
        except Exception as e:
            st.warning(f"⚠️ Layer RGB gagal dimuat: {e}")

    # Layer FDI
    if tampil_fdi:
        try:
            s2_fdi = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                      .filterDate(str(tgl_mulai), str(tgl_akhir))
                      .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', tutupan_awan))
                      .median())
            fdi = s2_fdi.expression(
                'NIR - (RE1 + (SWIR - RE1) * ((833.0 - 740.0) / (1614.0 - 740.0)) * 10)',
                {'NIR': s2_fdi.select('B8'), 'RE1': s2_fdi.select('B6'), 'SWIR': s2_fdi.select('B11')}
            ).rename('FDI')
            water_mask = s2_fdi.normalizedDifference(['B3', 'B8']).gt(0.05)
            fdi_masked = fdi.updateMask(water_mask).updateMask(fdi.gt(50))
            fdi_id = fdi_masked.getMapId({
                'min': 50, 'max': 600,
                'palette': ['#ffffb2', '#fecc5c', '#fd8d3c', '#f03b20', '#bd0026']
            })
            folium.TileLayer(
                tiles=fdi_id['tile_fetcher'].url_format,
                attr='FDI Plastic Detection | GEE',
                name='🔴 Deteksi Plastik (FDI)',
                overlay=True, control=True
            ).add_to(m)
        except Exception as e:
            st.warning(f"⚠️ Layer FDI gagal dimuat: {e}")

    # Marker hotspot
    if tampil_marker:
        for sp in spots:
            color = LEVEL_COLOR.get(sp["level"], "#999")
            popup_html = f"""
            <div style='font-family:sans-serif;min-width:210px;padding:4px'>
                <b style='color:{color};font-size:1rem'>{sp['name']}</b><br>
                <span style='background:{color};color:white;border-radius:10px;
                             padding:1px 10px;font-size:0.75rem'>{sp['level']}</span>
                <p style='margin:8px 0 0;font-size:0.85rem'>{sp['info']}</p>
            </div>"""
            folium.CircleMarker(
                location=[sp["lat"], sp["lon"]],
                radius=10, color=color, fill=True,
                fill_color=color, fill_opacity=0.85,
                popup=folium.Popup(popup_html, max_width=260),
                tooltip=f"📍 {sp['name']} — {sp['level']}"
            ).add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    # Legend
    legend = """
    <div style='position:fixed;bottom:30px;left:30px;z-index:1000;
                background:rgba(10,61,98,0.93);color:white;
                padding:14px 18px;border-radius:12px;font-size:0.8rem;
                border:1px solid rgba(255,255,255,0.2);line-height:1.9'>
        <b>🔴 Indeks FDI</b><br>
        <span style='color:#ffffb2'>■</span> Rendah &nbsp;
        <span style='color:#fd8d3c'>■</span> Sedang &nbsp;
        <span style='color:#bd0026'>■</span> Tinggi<br>
        <b>📍 Hotspot Sampah</b><br>
        <span style='color:#e63946'>●</span> Kritis &nbsp;
        <span style='color:#f4a261'>●</span> Tinggi &nbsp;
        <span style='color:#2a9d8f'>●</span> Sedang
    </div>"""
    m.get_root().html.add_child(folium.Element(legend))

    st_folium(m, width="100%", height=630, returned_objects=[])

# ══ TAB STATISTIK ═════════════════════════════
with tab_stat:
    st.markdown("### 📊 Statistik Sampah Plastik Laut Indonesia")

    c1, c2, c3, c4 = st.columns(4)
    cards = [
        ("6.8 jt ton", "Plastik/tahun masuk laut Indonesia"),
        ("#2 Dunia",   "Penghasil sampah plastik laut terbesar"),
        ("3.700+ km",  "Panjang pantai tercemar plastik"),
        ("Rp 1.3T",    "Kerugian sektor perikanan/tahun"),
    ]
    for col, (val, lbl) in zip([c1, c2, c3, c4], cards):
        with col:
            st.markdown(f"""<div class='metric-card'>
                <div class='val'>{val}</div>
                <div class='lbl'>{lbl}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_a, col_b = st.columns(2)

    with col_a:
        df_tren = pd.DataFrame({
            "Tahun": [2019, 2020, 2021, 2022, 2023, 2024],
            "Estimasi Plastik (ribu ton)": [5800, 6000, 6100, 6300, 6500, 6800]
        })
        fig1 = px.area(df_tren, x="Tahun", y="Estimasi Plastik (ribu ton)",
                       title="📈 Tren Sampah Plastik ke Laut Indonesia",
                       color_discrete_sequence=["#0a9396"])
        fig1.update_layout(plot_bgcolor="#f0f9ff", paper_bgcolor="white", title_font_size=14)
        st.plotly_chart(fig1, use_container_width=True)

    with col_b:
        df_wilayah = pd.DataFrame({
            "Wilayah": ["Jawa", "Sumatera", "Kalimantan", "Sulawesi", "Papua", "Bali+NTT"],
            "Kontribusi (%)": [42, 25, 14, 10, 5, 4]
        })
        fig2 = px.bar(df_wilayah, x="Wilayah", y="Kontribusi (%)",
                      title="🗺️ Kontribusi Sampah Plastik per Pulau",
                      color="Kontribusi (%)",
                      color_continuous_scale=["#a8dadc", "#e63946"])
        fig2.update_layout(plot_bgcolor="#f0f9ff", paper_bgcolor="white", title_font_size=14)
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("### 📍 Daftar Hotspot Sampah (Data Penelitian)")
    semua = [s for v in HOTSPOTS.values() for s in v]
    df_s  = pd.DataFrame([{
        "Lokasi": s["name"], "Tingkat": s["level"],
        "Lat": s["lat"], "Lon": s["lon"], "Keterangan": s["info"]
    } for s in semua])

    def warnai(val):
        return {"Kritis": "background-color:#ffe0e0",
                "Tinggi": "background-color:#fff3e0",
                "Sedang": "background-color:#e0f5f5"}.get(val, "")

    st.dataframe(df_s.style.applymap(warnai, subset=["Tingkat"]),
                 use_container_width=True, hide_index=True)

# ══ TAB INFO ══════════════════════════════════
with tab_info:
    st.markdown("### ℹ️ Metode, Data & Referensi")

    for box in [
        ("<b>🛰️ Data Satelit: Sentinel-2 SR Harmonized</b><br>"
         "Resolusi 10–20 meter, revisit 5 hari, dari ESA/Copernicus. "
         "Diproses menggunakan Google Earth Engine untuk komposit median bebas awan."),
        ("<b>📐 Algoritma: Floating Debris Index (FDI)</b><br>"
         "Dikembangkan oleh <i>Biermann et al. (2020, Scientific Reports)</i>:<br><br>"
         "<code>FDI = NIR − [RE1 + (SWIR − RE1) × (λNIR−λRE1)/(λSWIR−λRE1) × 10]</code><br><br>"
         "Nilai FDI tinggi (merah) = material mengapung dengan reflektansi berbeda dari air bersih "
         "— berpotensi plastik, ganggang, atau limbah organik."),
        ("<b>⚠️ Limitasi & Catatan</b><br>"
         "· FDI tidak 100% spesifik plastik — ganggang laut (Sargassum) juga bernilai tinggi<br>"
         "· Perlu validasi lapangan untuk konfirmasi<br>"
         "· Tutupan awan/kabut menyebabkan area data kosong<br>"
         "· Resolusi 10m kurang optimal untuk plastik skala kecil"),
        ("<b>📚 Referensi</b><br>"
         "· Biermann et al. (2020). Finding Plastic Patches in Coastal Waters. <i>Scientific Reports</i><br>"
         "· Topouzelis et al. (2019). Detection of floating plastics from satellite. <i>IJRS</i><br>"
         "· BRIN (2023). Laporan Pemantauan Sampah Pesisir Indonesia"),
    ]:
        st.markdown(f"<div class='info-box'>{box}</div>", unsafe_allow_html=True)
