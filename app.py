from flask import Flask, render_template, request
import pandas as pd
import folium
import re

app = Flask(__name__)

# Load data sekali saja
df = pd.read_csv("static/database_penelitian.csv")


# === Helper: ubah link Google Drive jadi URL gambar langsung ===
def gdrive_view_url(raw):
    """
    Input:
      - Link share Google Drive (https://drive.google.com/file/d/FILE_ID/view?...), atau
      - Hanya FILE_ID saja

    Output:
      - https://drive.google.com/uc?export=view&id=FILE_ID
    """
    if pd.isna(raw):
        return None

    s = str(raw).strip()
    if not s:
        return None

    file_id = None

    if "drive.google.com" in s:
        m = re.search(r"/d/([^/]+)", s)           # pola /d/FILE_ID/
        if m:
            file_id = m.group(1)
        else:
            m = re.search(r"[?&]id=([^&]+)", s)   # pola ?id=FILE_ID
            if m:
                file_id = m.group(1)
    else:
        # diasumsikan langsung file id
        file_id = s

    if not file_id:
        return None

    return f"https://drive.google.com/uc?export=view&id={file_id}"


# === Helper: parsing float yang tahan format lokal (koma/titik) ===
def to_float_or_none(raw):
    if raw is None:
        return None
    s = str(raw).strip()
    if s == "":
        return None

    try:
        # contoh: "1.234,56" -> 1234.56 ; "1,234.56" -> 1234.56
        if "," in s and "." in s:
            s = s.replace(".", "").replace(",", ".")
        elif "," in s and "." not in s:
            s = s.replace(",", ".")
        return float(s)
    except Exception:
        return None


@app.route("/", methods=["GET", "POST"])
def index():
    # --- Ambil nilai filter dari form (GET atau POST) ---
    kecamatan_raw = (request.values.get("kecamatan") or "").strip()
    kelurahan_raw = (request.values.get("kelurahan") or "").strip()
    stasiun_raw   = (request.values.get("stasiun") or "").strip()
    fk_raw        = (request.values.get("fk_min") or "").strip()
    phi_raw       = (request.values.get("phi_min") or "").strip()

    fk_min = to_float_or_none(fk_raw)
    phi_min = to_float_or_none(phi_raw)

    # --- Salin dataframe dan pastikan kolom numerik benar2 numeric ---
    data = df.copy()

    if "Nilai_Faktor_Keamanan_(FK)" in data.columns:
        data["Nilai_Faktor_Keamanan_(FK)"] = pd.to_numeric(
            data["Nilai_Faktor_Keamanan_(FK)"], errors="coerce"
        )
    if "Sudut_Geser_Dalam" in data.columns:
        data["Sudut_Geser_Dalam"] = pd.to_numeric(
            data["Sudut_Geser_Dalam"], errors="coerce"
        )

    # --- Buat mask filter (semua baris True di awal) ---
    mask = pd.Series(True, index=data.index)

    # Filter Kecamatan
    if kecamatan_raw:
        mask &= data["Kecamatan"].astype(str).str.contains(
            kecamatan_raw, case=False, na=False
        )

    # Filter Kelurahan
    if kelurahan_raw:
        mask &= data["Kelurahan"].astype(str).str.contains(
            kelurahan_raw, case=False, na=False
        )

    # Filter Stasiun / Nama_STA
    if stasiun_raw:
        mask &= data["Nama_STA"].astype(str).str.contains(
            stasiun_raw, case=False, na=False
        )

    # Filter Nilai FK >= fk_min
    if fk_min is not None:
        mask &= data["Nilai_Faktor_Keamanan_(FK)"] >= fk_min

    # Filter Sudut Geser Dalam >= phi_min
    if phi_min is not None:
        mask &= data["Sudut_Geser_Dalam"] >= phi_min

    filtered = data[mask].copy()

    # --- Tentukan center map (pakai rata-rata titik hasil filter / seluruh data) ---
    if filtered.empty:
        center_lat = df["lat"].mean()
        center_lon = df["lon"].mean()
    else:
        center_lat = filtered["lat"].mean()
        center_lon = filtered["lon"].mean()

    m = folium.Map(location=[center_lat, center_lon], zoom_start=11)

    # --- Tambahkan marker untuk setiap titik hasil filter ---
    for _, row in filtered.iterrows():
        # Ambil link dari CSV apa adanya
        raw_link = row.get("Foto_Singkapan")
        
        # Kalau csv lama: link /file/d/...
        # Kalau csv baru: sudah uc?export=view...
        # Dua-duanya kita olah lagi supaya aman
        foto_url = gdrive_view_url(raw_link)

        popup_html = f"""
        <div style="width:240px">
        <b>{row['Nama_STA']}</b><br>
        Kecamatan: {row['Kecamatan']}<br>
        Kelurahan: {row['Kelurahan']}<br>
        Nilai Faktor Keamanan (FK): {row['Nilai_Faktor_Keamanan_(FK)']}<br>
        Sudut Geser Dalam (φ): {row['Sudut_Geser_Dalam']}°
        """

        # Tambah link untuk buka foto di tab baru (selalu raw_link biar kelihatan persis)
        if raw_link:
            popup_html += f'<br><a href="{raw_link}" target="_blank">Buka foto singkapan</a>'

        popup_html += "</div>"

        folium.Marker(
            location=[row["lat"], row["lon"]],
            popup=folium.Popup(popup_html, max_width=260),
            tooltip=row["Nama_STA"],
        ).add_to(m)


    map_html = m._repr_html_()

    return render_template(
        "home.html",
        map_html=map_html,
        kecamatan=kecamatan_raw,
        kelurahan=kelurahan_raw,
        stasiun=stasiun_raw,
        fk_min=fk_raw,
        phi_min=phi_raw,
    )


if __name__ == "__main__":
    app.run(debug=True)