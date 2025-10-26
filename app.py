from flask import Flask
from flask import render_template, request
import pandas as pd
import folium

app = Flask(__name__)
df = pd.read_csv("static/database_penelitian.csv")

@app.route('/', methods=['GET', 'POST'])
def hello_world():
    # --- Ambil input (GET/POST) ---
    # Gunakan request.values agar GET/POST sama-sama diterima
    min_pop_raw = (request.values.get('min_pop') or '').strip()
    keyword     = (request.values.get('keyword') or '').strip()

# --- Parse float yang tahan format lokal (mis. "1.234,56") ---
    def to_float(x, default=0.0):
        try:
            s = str(x).strip()
            if s == '':
                return default
# terima "1.234,56" → 1234.56 ; "1,234.56" → 1234.56
            if "," in s and "." in s:
                s = s.replace(".", "").replace(",", ".")
            elif "," in s and "." not in s:
                s = s.replace(",", ".")
            return float(s)
        except Exception:
            return default

    min_pop = to_float(min_pop_raw, default=0.0)

# --- Siapkan kolom numerik sebagai numeric (coerce NaN) ---
    num_cols = ["Nilai_Faktor_Keamanan_(FK)", "Sudut_Geser_Dalam"]
    data = df.copy()
    for c in num_cols:
        if c in data.columns:
            data[c] = pd.to_numeric(data[c], errors='coerce')

# --- Bangun mask numerik (kedua kolom >= min_pop) ---
    mask_num = pd.Series(True, index=data.index)
    if "Nilai_Faktor_Keamanan_(FK)" in data.columns:
        mask_num &= (data["Nilai_Faktor_Keamanan_(FK)"] >= min_pop)
    if "Sudut_Geser_Dalam" in data.columns:
        mask_num &= (data["Sudut_Geser_Dalam"] >= min_pop)

# --- Bangun mask string (OR di 3 kolom). Lewati jika keyword kosong ---
    if keyword:
        kw = keyword.lower()
        m1 = data["Nama_STA"].astype(str).str.lower().str.contains(kw, na=False) if "Nama_STA" in data.columns else False
        m2 = data["Kecamatan"].astype(str).str.lower().str.contains(kw, na=False) if "Kecamatan" in data.columns else False
        m3 = data["Kelurahan"].astype(str).str.lower().str.contains(kw, na=False) if "Kelurahan" in data.columns else False
        mask_str = (m1 | m2 | m3)
    else:
        mask_str = pd.Series(True, index=data.index)

# --- Gabungkan ---
    filtered = data[mask_num & mask_str]


    m = folium.Map(location=[-0.5022, 117.1536], zoom_start=11)
    for _, row in df.iterrows():
        popup = f"{row['Nama_STA']}<br>Kecamatan: {row['Kecamatan']}<br>Kelurahan: {row['Kelurahan']}<br>Nilai Faktor Keamanan: {row['Nilai_Faktor_Keamanan_(FK)']}<br>Sudut Geser Dalam: {row['Sudut_Geser_Dalam']}"
        folium.Marker(
            location=[row["lat"], row["lon"]],
            popup=popup,
            tooltip=row["Nama_STA"]
        ).add_to(m)

    # Save map to HTML string
    map_html = m._repr_html_()
    return render_template('home.html', map_html=map_html)

if __name__ == '__main__':
    app.run(debug=True)