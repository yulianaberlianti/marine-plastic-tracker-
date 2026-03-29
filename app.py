import streamlit as st
import ee
import folium
from folium.plugins import Draw, MeasureControl
from streamlit_folium import st_folium
import json
import pandas as pd
import plotly.express as px
from datetime import date
import io
import base64

# ─────────────────────────────────────────────
# 1. KONFIGURASI HALAMAN
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="🌊 Marine Plastic Tracker", page_icon="🌊")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=DM+Sans:wght@300;400;500&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.main-header {
    background: linear-gradient(135deg, #0a3d62 0%, #1a6fa8 50%, #0a9396 100%);
    padding: 2rem 2.5rem; border-radius: 16px; color: white; margin-bottom: 1.5rem;
    box-shadow: 0 8px 32px rgba(10,61,98,0.3);
}
.main-header h1 { font-family:'Syne',sans-serif; font-size:2.4rem; margin:0; font-weight:800; letter-spacing:-0.5px; }
.main-header p  { font-size:1rem; margin:0.5rem 0 0; opacity:0.85; }
.metric-card {
    background: linear-gradient(135deg, #0a3d62, #1e6f9f);
    border-radius: 12px; padding: 1.2rem; color: white; text-align: center;
    border: 1px solid rgba(255,255,255,0.15); height: 100%;
}
.metric-card .val { font-family:'Syne',sans-serif; font-size:1.9rem; font-weight:700; }
.metric-card .lbl { font-size:0.77rem; opacity:0.82; margin-top:5px; line-height:1.4; }
.info-box {
    background: #f0f9ff; border-left: 4px solid #0a9396;
    border-radius: 8px; padding: 1rem 1.2rem; margin: 0.6rem 0; font-size:0.93rem;
}
.legend-box {
    background: #1a2a3a; border-radius: 12px; padding: 1.2rem 1.4rem;
    color: white; margin-bottom: 1rem; border: 1px solid rgba(255,255,255,0.1);
}
.legend-box h4 { font-family:'Syne',sans-serif; margin:0 0 0.8rem; font-size:0.95rem; color:#7dd3fc; }
.legend-row { display:flex; align-items:flex-start; gap:10px; margin:6px 0; font-size:0.82rem; }
.swatch       { width:16px; height:16px; border-radius:3px; flex-shrink:0; margin-top:2px; }
.swatch-circle{ width:14px; height:14px; border-radius:50%; flex-shrink:0; margin-top:2px; }
.draw-info {
    background: linear-gradient(135deg, #064e3b, #065f46);
    border-radius: 10px; padding: 0.9rem 1.1rem; color: white;
    border: 1px solid rgba(255,255,255,0.15); margin-bottom: 0.8rem; font-size:0.88rem;
}
.coord-display {
    background: #0f172a; border-radius: 8px; padding: 0.7rem 1rem;
    color: #94a3b8; font-family: monospace; font-size: 0.8rem;
    border: 1px solid rgba(255,255,255,0.08); margin-top: 0.5rem;
}
.dl-section {
    background: #f8fafc; border-radius: 12px; padding: 1.2rem 1.4rem;
    border: 1px solid #e2e8f0; margin-bottom: 1.2rem;
}
.dl-section h4 { margin: 0 0 0.5rem; color: #0a3d62; font-family:'Syne',sans-serif; }
.dl-note { font-size:0.8rem; color:#64748b; margin-bottom:0.8rem; }
.stButton>button {
    background: linear-gradient(135deg, #0a3d62, #0a9396);
    color: white; border: none; border-radius: 8px;
    padding: 0.55rem 1.5rem; font-weight: 600; font-size: 0.92rem;
}
div[data-testid="stSidebar"] { background: #0d2137; }
div[data-testid="stSidebar"] label,
div[data-testid="stSidebar"] p,
div[data-testid="stSidebar"] span,
div[data-testid="stSidebar"] .stMarkdown { color: #e2e8f0 !important; }
div[data-testid="stSidebar"] h2,
div[data-testid="stSidebar"] h3 { color: #7dd3fc !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 2. DATA
# ─────────────────────────────────────────────
HOTSPOTS = {
    "Teluk Jakarta": [
        {"name":"Muara Ciliwung",          "lat":-6.117,"lon":106.835,"level":"Kritis",
         "info":"Sungai Ciliwung membawa ±150 ton sampah/hari ke laut"},
        {"name":"Muara Angke",             "lat":-6.102,"lon":106.741,"level":"Kritis",
         "info":"Kawasan nelayan dengan akumulasi plastik tinggi"},
        {"name":"Kepulauan Seribu (Sel.)", "lat":-5.850,"lon":106.650,"level":"Sedang",
         "info":"Arus membawa sampah dari daratan ke kepulauan"},
        {"name":"Muara Bekasi",            "lat":-6.090,"lon":107.000,"level":"Tinggi",
         "info":"Kawasan industri dengan limbah plastik tinggi"},
    ],
    "Pesisir Jawa Barat": [
        {"name":"Muara Citarum", "lat":-6.016,"lon":107.489,"level":"Kritis",
         "info":"Citarum pernah disebut sungai terkotor di dunia"},
        {"name":"Pantai Eretan","lat":-6.250,"lon":108.220,"level":"Tinggi",
         "info":"Akumulasi sampah dari arus laut Jawa"},
    ],
    "Pesisir Jawa Tengah": [
        {"name":"Muara Serayu",  "lat":-7.740,"lon":109.010,"level":"Sedang",
         "info":"DAS Serayu membawa material dari pegunungan"},
        {"name":"Semarang Utara","lat":-6.940,"lon":110.430,"level":"Tinggi",
         "info":"Kawasan pelabuhan dengan polusi plastik"},
    ],
    "Pesisir Jawa Timur": [
        {"name":"Muara Brantas (Surabaya)","lat":-7.190,"lon":112.730,"level":"Kritis",
         "info":"Brantas salah satu DAS paling tercemar plastik"},
        {"name":"Selat Madura",           "lat":-7.120,"lon":112.850,"level":"Tinggi",
         "info":"Arus sempit mengkonsentrasikan sampah plastik"},
    ],
    "Kalimantan Selatan": [
        {"name":"Muara Barito (Banjarmasin)","lat":-3.320,"lon":114.590,"level":"Tinggi",
         "info":"Kota sungai dengan banyak aktivitas di atas air"},
    ],
    "Sulawesi Selatan": [
        {"name":"Teluk Makassar","lat":-5.130,"lon":119.410,"level":"Tinggi",
         "info":"Kota besar dengan pengelolaan sampah yang masih kurang"},
    ],
}

AREA_COORDS = {
    "📍 Pilih dari daftar →": None,
    "Teluk Jakarta":           {"lat":-6.05, "lon":106.83,"zoom":11},
    "Pesisir Jawa Barat":      {"lat":-6.20, "lon":107.80,"zoom":9},
    "Pesisir Jawa Tengah":     {"lat":-6.90, "lon":110.20,"zoom":9},
    "Pesisir Jawa Timur":      {"lat":-7.20, "lon":112.70,"zoom":9},
    "Kalimantan Selatan":      {"lat":-3.40, "lon":114.60,"zoom":9},
    "Sulawesi Selatan":        {"lat":-5.10, "lon":119.40,"zoom":9},
    "Seluruh Indonesia":       {"lat":-2.50, "lon":118.00,"zoom":5},
}

LEVEL_COLOR = {"Kritis":"#e63946","Tinggi":"#f4a261","Sedang":"#2a9d8f"}

# ─────────────────────────────────────────────
# 3. GEE LOGIN
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
# 4. HELPER: GeoTIFF download link
# ─────────────────────────────────────────────
def get_geotiff_url(ee_image, region_geojson, band_name, description):
    """Buat URL download GeoTIFF dari GEE."""
    try:
        if region_geojson:
            geom = ee.Geometry(region_geojson["geometry"])
        else:
            # Default: Teluk Jakarta
            geom = ee.Geometry.Rectangle([106.6, -6.3, 107.1, -5.8])

        url = ee_image.getDownloadURL({
            'name':        description,
            'bands':       [band_name],
            'region':      geom,
            'scale':       30,
            'crs':         'EPSG:4326',
            'fileFormat':  'GeoTIFF',
        })
        return url, None
    except Exception as e:
        return None, str(e)

# ─────────────────────────────────────────────
# 5. HEADER
# ─────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🌊 Marine Plastic Tracker</h1>
    <p>Deteksi sampah plastik laut · Sentinel-2 + Google Earth Engine · Indonesia</p>
</div>
""", unsafe_allow_html=True)

if not gee_ok:
    st.error(f"❌ Gagal Login GEE: {gee_msg}")
    st.stop()

st.success("✅ Google Earth Engine terhubung!")

# ─────────────────────────────────────────────
# 6. SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Pengaturan Analisis")
    st.markdown("---")

    area_pilihan = st.selectbox("🗺️ Area Preset", list(AREA_COORDS.keys()))

    st.markdown("### 📅 Rentang Tanggal")
    c1, c2 = st.columns(2)
    with c1:
        tgl_mulai = st.date_input("Mulai", value=date(2024,1,1),
                                   min_value=date(2019,1,1), max_value=date(2025,12,31))
    with c2:
        tgl_akhir = st.date_input("Akhir", value=date(2024,12,31),
                                   min_value=date(2019,1,1), max_value=date(2025,12,31))

    tutupan_awan = st.slider("☁️ Maks. Tutupan Awan (%)", 0, 50, 10)

    st.markdown("### 🗺️ Layer Peta")
    tampil_rgb    = st.checkbox("🛰️ Citra Asli (RGB)",      value=True)
    tampil_fdi    = st.checkbox("🔴 Deteksi Plastik (FDI)", value=True)
    tampil_marker = st.checkbox("📍 Hotspot Sampah",         value=True)

    st.markdown("---")
    st.markdown("### ✏️ Gambar Area Sendiri")
    st.markdown("""
    <div style='font-size:0.8rem;color:#94a3b8;line-height:1.8'>
    Toolbar di pojok <b>kanan atas peta</b>:<br>
    ▭ Rectangle — kotak<br>
    ⬠ Polygon — bentuk bebas<br>
    🔵 Circle — lingkaran<br>
    📏 Measure — ukur jarak/luas<br>
    🗑️ Delete — hapus gambar
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("""
    <div style='font-size:0.73rem;color:#64748b;line-height:1.7'>
    <b style='color:#7dd3fc'>Sumber Data</b><br>
    · Sentinel-2 SR (ESA/Copernicus)<br>
    · Biermann et al. (2020) — FDI<br>
    · BRIN Marine Debris Database
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 7. TABS
# ─────────────────────────────────────────────
tab_peta, tab_legenda, tab_stat, tab_dl, tab_info = st.tabs([
    "🗺️ Peta Analisis", "🎨 Legenda", "📊 Statistik", "⬇️ Download Data", "ℹ️ Metode"
])

# ══════════════════════════════════════════════
# TAB PETA
# ══════════════════════════════════════════════
with tab_peta:
    if area_pilihan != "📍 Pilih dari daftar →" and AREA_COORDS[area_pilihan]:
        coord = AREA_COORDS[area_pilihan]
        center_lat, center_lon, zoom = coord["lat"], coord["lon"], coord["zoom"]
    else:
        center_lat, center_lon, zoom = -2.5, 118.0, 5

    spots = HOTSPOTS.get(area_pilihan, [s for v in HOTSPOTS.values() for s in v])

    m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom,
                   tiles="CartoDB dark_matter")

    # Layer RGB
    if tampil_rgb:
        try:
            s2 = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                  .filterDate(str(tgl_mulai), str(tgl_akhir))
                  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', tutupan_awan))
                  .median())
            rgb_id = s2.getMapId({'bands':['B4','B3','B2'],'min':0,'max':3000,'gamma':1.4})
            folium.TileLayer(tiles=rgb_id['tile_fetcher'].url_format,
                             attr='Sentinel-2 RGB | ESA/GEE',
                             name='🛰️ Citra Asli (RGB)',
                             overlay=True, control=True).add_to(m)
            st.session_state["s2_image"] = s2   # simpan untuk export
        except Exception as e:
            st.warning(f"⚠️ Layer RGB gagal: {e}")

    # Layer FDI
    if tampil_fdi:
        try:
            s2f = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                   .filterDate(str(tgl_mulai), str(tgl_akhir))
                   .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', tutupan_awan))
                   .median())
            fdi = s2f.expression(
                'NIR - (RE1 + (SWIR - RE1) * ((833.0-740.0)/(1614.0-740.0)) * 10)',
                {'NIR':s2f.select('B8'),'RE1':s2f.select('B6'),'SWIR':s2f.select('B11')}
            ).rename('FDI')
            water = s2f.normalizedDifference(['B3','B8']).gt(0.05)
            fdi_m = fdi.updateMask(water).updateMask(fdi.gt(50))
            fdi_id = fdi_m.getMapId({
                'min':50,'max':600,
                'palette':['#ffffb2','#fecc5c','#fd8d3c','#f03b20','#bd0026']
            })
            folium.TileLayer(tiles=fdi_id['tile_fetcher'].url_format,
                             attr='FDI | GEE', name='🔴 Deteksi Plastik (FDI)',
                             overlay=True, control=True).add_to(m)
            st.session_state["fdi_image"] = fdi_m  # simpan untuk export
        except Exception as e:
            st.warning(f"⚠️ Layer FDI gagal: {e}")

    # Marker hotspot
    if tampil_marker:
        for sp in spots:
            color = LEVEL_COLOR.get(sp["level"],"#999")
            popup_html = f"""
            <div style='font-family:sans-serif;min-width:210px;padding:6px'>
                <b style='color:{color};font-size:0.95rem'>{sp['name']}</b><br>
                <span style='background:{color};color:white;border-radius:10px;
                             padding:1px 10px;font-size:0.73rem;font-weight:600'>{sp['level']}</span>
                <p style='margin:8px 0 0;font-size:0.83rem;color:#334155'>{sp['info']}</p>
            </div>"""
            folium.CircleMarker(
                location=[sp["lat"], sp["lon"]], radius=10,
                color=color, fill=True, fill_color=color, fill_opacity=0.85,
                popup=folium.Popup(popup_html, max_width=260),
                tooltip=f"📍 {sp['name']} — {sp['level']}"
            ).add_to(m)

    # Draw Tools (Rectangle + Polygon + Circle + Polyline)
    Draw(
        export=True,
        draw_options={
            "rectangle":    {"shapeOptions": {"color":"#00d4ff","weight":2,"fillOpacity":0.1}},
            "polygon":      {"shapeOptions": {"color":"#00ff88","weight":2,"fillOpacity":0.1}},
            "circle":       {"shapeOptions": {"color":"#ffcc00","weight":2,"fillOpacity":0.1}},
            "polyline":     {"shapeOptions": {"color":"#ff6b6b","weight":2}},
            "marker":       True,
            "circlemarker": False,
        },
        edit_options={"edit": True}
    ).add_to(m)

    MeasureControl(position='topright',
                   primary_length_unit='kilometers',
                   primary_area_unit='sqkilometers').add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    # Legend overlay di peta
    legend_html = """
    <div style='position:fixed;bottom:28px;left:28px;z-index:1000;
                background:rgba(13,33,55,0.94);color:white;
                padding:14px 18px;border-radius:12px;font-size:0.78rem;
                border:1px solid rgba(255,255,255,0.15);line-height:2;
                box-shadow:0 4px 20px rgba(0,0,0,0.4)'>
        <div style='font-weight:700;font-size:0.85rem;color:#7dd3fc;margin-bottom:4px'>🎨 Legenda</div>
        <div style='color:#94a3b8;font-size:0.7rem;margin-bottom:5px'>Indeks FDI</div>
        <div><span style='background:#ffffb2;display:inline-block;width:12px;height:12px;border-radius:2px'></span> &nbsp;Rendah</div>
        <div><span style='background:#fd8d3c;display:inline-block;width:12px;height:12px;border-radius:2px'></span> &nbsp;Sedang</div>
        <div><span style='background:#bd0026;display:inline-block;width:12px;height:12px;border-radius:2px'></span> &nbsp;Tinggi</div>
        <div style='margin-top:6px;color:#94a3b8;font-size:0.7rem;margin-bottom:4px'>Hotspot</div>
        <div><span style='background:#e63946;display:inline-block;width:12px;height:12px;border-radius:50%'></span> &nbsp;Kritis</div>
        <div><span style='background:#f4a261;display:inline-block;width:12px;height:12px;border-radius:50%'></span> &nbsp;Tinggi</div>
        <div><span style='background:#2a9d8f;display:inline-block;width:12px;height:12px;border-radius:50%'></span> &nbsp;Sedang</div>
    </div>"""
    m.get_root().html.add_child(folium.Element(legend_html))

    # Screenshot HTML (tombol di dalam peta)
    screenshot_js = """
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
    <div style='position:fixed;top:80px;right:10px;z-index:9999'>
        <button onclick="
            html2canvas(document.querySelector('.folium-map')).then(canvas => {
                var link = document.createElement('a');
                link.download = 'marine_plastic_map.png';
                link.href = canvas.toDataURL();
                link.click();
            });
        " style='background:rgba(13,33,55,0.9);color:white;border:1px solid rgba(255,255,255,0.3);
                 border-radius:8px;padding:6px 12px;cursor:pointer;font-size:0.8rem;font-weight:600'>
            📸 Screenshot PNG
        </button>
    </div>"""
    m.get_root().html.add_child(folium.Element(screenshot_js))

    # Render peta
    map_data = st_folium(m, width="100%", height=640,
                          returned_objects=["all_drawings","last_active_drawing","bounds"])

    # Tampilkan koordinat area gambar
    if map_data and map_data.get("all_drawings"):
        drawings = map_data["all_drawings"]
        if drawings:
            st.markdown("### ✏️ Area yang Kamu Gambar")
            st.markdown(f"""<div class='draw-info'>
                ✅ <b>{len(drawings)} area</b> digambar. Koordinat siap di-download di tab ⬇️ Download Data.
            </div>""", unsafe_allow_html=True)
            st.session_state["drawn_shapes"]  = drawings
            st.session_state["drawn_bounds"]  = map_data.get("bounds")

            for i, shape in enumerate(drawings):
                geom_type = shape.get("geometry",{}).get("type","Unknown")
                coords    = shape.get("geometry",{}).get("coordinates",[])
                st.markdown(f"""<div class='coord-display'>
                🔷 Shape {i+1} — <b>{geom_type}</b><br>
                {json.dumps(coords, indent=2)[:400]}{'...' if len(str(coords))>400 else ''}
                </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style='background:#0f172a;border-radius:8px;padding:0.8rem 1rem;
                    color:#64748b;font-size:0.85rem;text-align:center;margin-top:0.5rem;
                    border:1px dashed rgba(255,255,255,0.1)'>
            ✏️ Gunakan toolbar di pojok kanan atas peta untuk menggambar area analisis sendiri
        </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════
# TAB LEGENDA
# ══════════════════════════════════════════════
with tab_legenda:
    st.markdown("### 🎨 Panduan Legenda & Interpretasi")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div class='legend-box'>
        <h4>🔴 Indeks FDI (Floating Debris Index)</h4>
        <div style='font-size:0.8rem;color:#94a3b8;margin-bottom:10px'>Anomali reflektansi NIR di permukaan air</div>
        <div class='legend-row'><div class='swatch' style='background:#ffffb2;border:1px solid #ccc'></div>
        <div><b>Kuning muda</b> — FDI 50–150 (Sangat Rendah)<br><span style='color:#94a3b8;font-size:0.75rem'>Busa laut / ganggang tipis</span></div></div>
        <div class='legend-row'><div class='swatch' style='background:#fecc5c'></div>
        <div><b>Kuning</b> — FDI 150–250 (Rendah)<br><span style='color:#94a3b8;font-size:0.75rem'>Sedimen / material organik tersuspensi</span></div></div>
        <div class='legend-row'><div class='swatch' style='background:#fd8d3c'></div>
        <div><b>Oranye</b> — FDI 250–400 (Sedang)<br><span style='color:#94a3b8;font-size:0.75rem'>Kemungkinan plastik / Sargassum</span></div></div>
        <div class='legend-row'><div class='swatch' style='background:#f03b20'></div>
        <div><b>Merah</b> — FDI 400–550 (Tinggi)<br><span style='color:#94a3b8;font-size:0.75rem'>Potensi kuat sampah plastik mengapung</span></div></div>
        <div class='legend-row'><div class='swatch' style='background:#bd0026'></div>
        <div><b>Merah tua</b> — FDI >550 (Sangat Tinggi)<br><span style='color:#94a3b8;font-size:0.75rem'>Konsentrasi debris sangat padat</span></div></div>
        </div>""", unsafe_allow_html=True)

        st.markdown("""
        <div class='legend-box'>
        <h4>🛰️ Citra RGB Sentinel-2</h4>
        <div style='font-size:0.8rem;color:#94a3b8;margin-bottom:10px'>Band B4-B3-B2 (Natural Color)</div>
        <div class='legend-row'><div class='swatch' style='background:#1a3a5c'></div><div><b>Biru gelap</b> — Air laut dalam</div></div>
        <div class='legend-row'><div class='swatch' style='background:#4a9eca'></div><div><b>Biru muda</b> — Air dangkal / jernih</div></div>
        <div class='legend-row'><div class='swatch' style='background:#8fbc8f'></div><div><b>Hijau kecoklatan</b> — Sedimen muara</div></div>
        <div class='legend-row'><div class='swatch' style='background:#f5f5f5'></div><div><b>Putih</b> — Awan (data tidak tersedia)</div></div>
        <div class='legend-row'><div class='swatch' style='background:#4a7c4e'></div><div><b>Hijau</b> — Vegetasi / mangrove</div></div>
        </div>""", unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class='legend-box'>
        <h4>📍 Hotspot Sampah</h4>
        <div style='font-size:0.8rem;color:#94a3b8;margin-bottom:10px'>Data penelitian lapangan & literatur</div>
        <div class='legend-row'><div class='swatch-circle' style='background:#e63946'></div>
        <div><b style='color:#e63946'>KRITIS</b> — Muara sungai besar<br><span style='color:#94a3b8;font-size:0.75rem'>Debit sampah >100 ton/hari, butuh intervensi segera</span></div></div>
        <div style='height:6px'></div>
        <div class='legend-row'><div class='swatch-circle' style='background:#f4a261'></div>
        <div><b style='color:#f4a261'>TINGGI</b> — Kawasan industri & pelabuhan<br><span style='color:#94a3b8;font-size:0.75rem'>Akumulasi signifikan, pemantauan rutin diperlukan</span></div></div>
        <div style='height:6px'></div>
        <div class='legend-row'><div class='swatch-circle' style='background:#2a9d8f'></div>
        <div><b style='color:#2a9d8f'>SEDANG</b> — Pesisir pulau & pantai terbuka<br><span style='color:#94a3b8;font-size:0.75rem'>Terpengaruh arus laut, monitoring berkala</span></div></div>
        </div>""", unsafe_allow_html=True)

        st.markdown("""
        <div class='legend-box'>
        <h4>✏️ Area Gambar Sendiri (Warna)</h4>
        <div class='legend-row'><div class='swatch' style='background:#00d4ff;height:4px;margin-top:7px'></div><div><b>Biru cyan</b> — Rectangle (kotak)</div></div>
        <div class='legend-row'><div class='swatch' style='background:#00ff88;height:4px;margin-top:7px'></div><div><b>Hijau neon</b> — Polygon bebas</div></div>
        <div class='legend-row'><div class='swatch' style='background:#ffcc00;height:4px;margin-top:7px'></div><div><b>Kuning</b> — Circle (lingkaran)</div></div>
        <div class='legend-row'><div class='swatch' style='background:#ff6b6b;height:4px;margin-top:7px'></div><div><b>Merah muda</b> — Polyline (garis)</div></div>
        </div>""", unsafe_allow_html=True)

        st.markdown("""
        <div class='legend-box'>
        <h4>⚠️ Catatan Interpretasi</h4>
        <div style='font-size:0.81rem;color:#94a3b8;line-height:1.8'>
        · FDI tinggi ≠ pasti plastik — Sargassum & sedimen juga tinggi<br>
        · Validasi lapangan diperlukan untuk konfirmasi<br>
        · Area putih = awan, data tidak tersedia<br>
        · Resolusi 10m optimal untuk patch >50m²<br>
        · Komposit median meminimalisir anomali sesaat
        </div></div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════
# TAB STATISTIK
# ══════════════════════════════════════════════
with tab_stat:
    st.markdown("### 📊 Statistik Sampah Plastik Laut Indonesia")
    c1,c2,c3,c4 = st.columns(4)
    for col,(val,lbl) in zip([c1,c2,c3,c4],[
        ("6.8 jt ton","Plastik/tahun masuk laut Indonesia"),
        ("#2 Dunia","Penghasil sampah plastik laut terbesar"),
        ("3.700+ km","Panjang pantai tercemar plastik"),
        ("Rp 1.3T","Kerugian sektor perikanan/tahun"),
    ]):
        with col:
            st.markdown(f"""<div class='metric-card'>
                <div class='val'>{val}</div><div class='lbl'>{lbl}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    ca,cb = st.columns(2)
    with ca:
        df_tren = pd.DataFrame({
            "Tahun":[2019,2020,2021,2022,2023,2024],
            "Estimasi Plastik (ribu ton)":[5800,6000,6100,6300,6500,6800]
        })
        fig1 = px.area(df_tren, x="Tahun", y="Estimasi Plastik (ribu ton)",
                       title="📈 Tren Sampah Plastik ke Laut Indonesia",
                       color_discrete_sequence=["#0a9396"])
        fig1.update_layout(plot_bgcolor="#f0f9ff", paper_bgcolor="white", title_font_size=14)
        st.plotly_chart(fig1, use_container_width=True)
    with cb:
        df_w = pd.DataFrame({
            "Wilayah":["Jawa","Sumatera","Kalimantan","Sulawesi","Papua","Bali+NTT"],
            "Kontribusi (%)":[42,25,14,10,5,4]
        })
        fig2 = px.bar(df_w, x="Wilayah", y="Kontribusi (%)",
                      title="🗺️ Kontribusi Sampah Plastik per Pulau",
                      color="Kontribusi (%)",
                      color_continuous_scale=["#a8dadc","#e63946"])
        fig2.update_layout(plot_bgcolor="#f0f9ff", paper_bgcolor="white", title_font_size=14)
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("### 📍 Tabel Hotspot Sampah")
    semua = [s for v in HOTSPOTS.values() for s in v]
    df_s  = pd.DataFrame([{"Lokasi":s["name"],"Tingkat":s["level"],
                            "Lat":s["lat"],"Lon":s["lon"],"Keterangan":s["info"]}
                           for s in semua])
    def warnai(val):
        return {"Kritis":"background-color:#ffe0e0","Tinggi":"background-color:#fff3e0",
                "Sedang":"background-color:#e0f5f5"}.get(val,"")
    st.dataframe(df_s.style.applymap(warnai, subset=["Tingkat"]),
                 use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════
# TAB DOWNLOAD
# ══════════════════════════════════════════════
with tab_dl:
    st.markdown("### ⬇️ Download Data")
    st.markdown("Unduh semua data analisis dalam berbagai format.")

    # ── 1. CSV Hotspot ───────────────────────
    st.markdown("<div class='dl-section'><h4>📍 1. Data Hotspot Sampah</h4>"
                "<p class='dl-note'>Semua lokasi hotspot beserta koordinat dan tingkat bahayanya</p>",
                unsafe_allow_html=True)
    semua_dl = [s for v in HOTSPOTS.values() for s in v]
    df_dl = pd.DataFrame([{"Nama Lokasi":s["name"],"Tingkat Bahaya":s["level"],
                            "Latitude":s["lat"],"Longitude":s["lon"],"Keterangan":s["info"]}
                           for s in semua_dl])
    col1, col2 = st.columns(2)
    with col1:
        st.download_button("⬇️ Download Hotspot.csv",
                           data=df_dl.to_csv(index=False).encode("utf-8"),
                           file_name="marine_plastic_hotspot.csv",
                           mime="text/csv", key="dl_csv")
    with col2:
        features = [{"type":"Feature",
                     "geometry":{"type":"Point","coordinates":[s["lon"],s["lat"]]},
                     "properties":{"name":s["name"],"level":s["level"],"info":s["info"]}}
                    for s in semua_dl]
        geojson_str = json.dumps({"type":"FeatureCollection","features":features},
                                  indent=2, ensure_ascii=False)
        st.download_button("⬇️ Download Hotspot.geojson",
                           data=geojson_str.encode("utf-8"),
                           file_name="marine_plastic_hotspot.geojson",
                           mime="application/geo+json", key="dl_geojson")
    st.markdown("</div>", unsafe_allow_html=True)

    # ── 2. CSV Statistik ─────────────────────
    st.markdown("<div class='dl-section'><h4>📊 2. Data Statistik Tren</h4>"
                "<p class='dl-note'>Estimasi volume sampah plastik ke laut Indonesia 2019–2024</p>",
                unsafe_allow_html=True)
    df_stat = pd.DataFrame({
        "Tahun":[2019,2020,2021,2022,2023,2024],
        "Estimasi Plastik (ribu ton)":[5800,6000,6100,6300,6500,6800]
    })
    st.download_button("⬇️ Download Statistik_Tren.csv",
                       data=df_stat.to_csv(index=False).encode("utf-8"),
                       file_name="marine_plastic_tren.csv",
                       mime="text/csv", key="dl_stat")
    st.markdown("</div>", unsafe_allow_html=True)

    # ── 3. GeoTIFF dari GEE ──────────────────
    st.markdown("<div class='dl-section'><h4>🛰️ 3. Download GeoTIFF (dari Google Earth Engine)</h4>"
                "<p class='dl-note'>File raster .tif yang bisa dibuka di QGIS / ArcGIS. "
                "Gambar area di peta dulu, lalu klik tombol di bawah.</p>",
                unsafe_allow_html=True)

    drawn = st.session_state.get("drawn_shapes", [])
    region_shape = drawn[0] if drawn else None

    col_tif1, col_tif2 = st.columns(2)
    with col_tif1:
        st.markdown("**Layer Citra RGB (B4-B3-B2)**")
        if st.button("🔗 Generate Link GeoTIFF RGB", key="btn_tif_rgb"):
            if "s2_image" in st.session_state:
                s2_img = st.session_state["s2_image"]
                rgb_export = s2_img.select(['B4','B3','B2'])
                with st.spinner("Membuat URL download..."):
                    url, err = get_geotiff_url(rgb_export, region_shape, 'B4', 'sentinel2_rgb')
                if url:
                    st.success("✅ Link siap!")
                    st.markdown(f"[📥 **Klik untuk download RGB.tif**]({url})", unsafe_allow_html=False)
                    st.caption("⚠️ Link aktif ±1 jam. Ukuran file tergantung luas area.")
                else:
                    st.error(f"Gagal: {err}")
            else:
                st.warning("Jalankan peta dulu dengan layer RGB aktif.")

    with col_tif2:
        st.markdown("**Layer FDI (Floating Debris Index)**")
        if st.button("🔗 Generate Link GeoTIFF FDI", key="btn_tif_fdi"):
            if "fdi_image" in st.session_state:
                fdi_img = st.session_state["fdi_image"]
                with st.spinner("Membuat URL download..."):
                    url, err = get_geotiff_url(fdi_img, region_shape, 'FDI', 'fdi_plastic')
                if url:
                    st.success("✅ Link siap!")
                    st.markdown(f"[📥 **Klik untuk download FDI.tif**]({url})", unsafe_allow_html=False)
                    st.caption("⚠️ Link aktif ±1 jam. Gambar area dulu di peta untuk wilayah spesifik.")
                else:
                    st.error(f"Gagal: {err}")
            else:
                st.warning("Jalankan peta dulu dengan layer FDI aktif.")

    st.info("💡 **Tips GeoTIFF:** Gambar kotak/polygon di peta terlebih dahulu untuk mengekspor area spesifik. Tanpa area gambar, akan menggunakan default Teluk Jakarta.")
    st.markdown("</div>", unsafe_allow_html=True)

    # ── 4. PNG Screenshot ────────────────────
    st.markdown("<div class='dl-section'><h4>📸 4. Screenshot Peta (PNG)</h4>"
                "<p class='dl-note'>Gunakan tombol 📸 Screenshot PNG yang ada di dalam peta (pojok kanan atas), "
                "atau gunakan cara alternatif di bawah.</p>",
                unsafe_allow_html=True)

    st.markdown("""
    **Cara screenshot peta:**
    - **Cara 1 (Otomatis):** Klik tombol **📸 Screenshot PNG** yang muncul di dalam peta
    - **Cara 2 (Manual):** Tekan `Ctrl+Shift+S` (Windows) atau `Cmd+Shift+4` (Mac) untuk screenshot layar
    - **Cara 3:** Klik kanan pada peta → "Save as image" (beberapa browser mendukung ini)
    """)
    st.markdown("</div>", unsafe_allow_html=True)

    # ── 5. Area Gambar → GeoJSON ─────────────
    st.markdown("<div class='dl-section'><h4>✏️ 5. Area yang Kamu Gambar</h4>"
                "<p class='dl-note'>Koordinat semua shape yang kamu gambar di peta</p>",
                unsafe_allow_html=True)
    if drawn:
        drawn_geojson = {"type":"FeatureCollection","features":drawn}
        drawn_str     = json.dumps(drawn_geojson, indent=2, ensure_ascii=False)
        st.success(f"✅ {len(drawn)} area siap di-download")
        col_a, col_b = st.columns(2)
        with col_a:
            st.download_button("⬇️ Download Area_Gambar.geojson",
                               data=drawn_str.encode("utf-8"),
                               file_name="marine_plastic_area_gambar.geojson",
                               mime="application/geo+json", key="dl_drawn")
        with col_b:
            # Konversi ke CSV koordinat sederhana
            rows = []
            for i, shape in enumerate(drawn):
                geom = shape.get("geometry",{})
                rows.append({
                    "shape_id": i+1,
                    "type": geom.get("type",""),
                    "coordinates_json": json.dumps(geom.get("coordinates",[]))
                })
            df_drawn = pd.DataFrame(rows)
            st.download_button("⬇️ Download Area_Gambar.csv",
                               data=df_drawn.to_csv(index=False).encode("utf-8"),
                               file_name="marine_plastic_area_gambar.csv",
                               mime="text/csv", key="dl_drawn_csv")
        with st.expander("👁️ Preview koordinat"):
            st.code(drawn_str[:800]+"...", language="json")
    else:
        st.info("ℹ️ Gambar area dulu di tab 🗺️ Peta Analisis menggunakan toolbar Draw.")
    st.markdown("</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════
# TAB INFO METODE
# ══════════════════════════════════════════════
with tab_info:
    st.markdown("### ℹ️ Metode, Data & Referensi")
    for box in [
        ("<b>🛰️ Sentinel-2 SR Harmonized</b><br>"
         "Resolusi 10–20m, revisit 5 hari (ESA/Copernicus). "
         "Diproses di Google Earth Engine sebagai komposit median bebas awan."),
        ("<b>📐 Floating Debris Index (FDI)</b><br>"
         "Dikembangkan Biermann et al. (2020, Scientific Reports):<br><br>"
         "<code>FDI = NIR − [RE1 + (SWIR − RE1) × (λNIR−λRE1)/(λSWIR−λRE1) × 10]</code><br><br>"
         "FDI tinggi = material mengapung dengan reflektansi berbeda dari air bersih."),
        ("<b>⚠️ Limitasi</b><br>"
         "· FDI tidak 100% spesifik plastik — Sargassum & sedimen juga tinggi<br>"
         "· Perlu validasi lapangan · Awan → data kosong<br>"
         "· Resolusi 10m kurang optimal untuk plastik skala kecil"),
        ("<b>📚 Referensi</b><br>"
         "· Biermann et al. (2020). Scientific Reports<br>"
         "· Topouzelis et al. (2019). IJRS<br>"
         "· BRIN (2023). Laporan Pemantauan Sampah Pesisir Indonesia"),
    ]:
        st.markdown(f"<div class='info-box'>{box}</div>", unsafe_allow_html=True)
