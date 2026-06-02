# InaWeather Early Warning Dashboard & Sistem Pakar Peringatan Dini Cuaca Nasional

**Mata Kuliah:** Sistem Pakar (03015108)  
**Program Studi:** Teknik Informatika, UHAMKA

---

## 1. Deskripsi & Tujuan Proyek
Proyek ini adalah pengembangan **InaWeather Warning**, sebuah aplikasi dashboard pemantau cuaca ekstrem dan peringatan dini nasional yang berjalan secara real-time. Aplikasi ini mengintegrasikan data resmi dari **BMKG (Badan Meteorologi, Klimatologi, dan Geofisika)** menggunakan standar **Common Alerting Protocol (CAP)** serta data observasi cuaca langsung dari **Open-Meteo API**. 

Sebagai bagian dari penilaian mata kuliah Sistem Pakar, dashboard ini juga mengintegrasikan **Simulator Sistem Pakar Berbasis Logika Fuzzy (Fuzzy Logic Inference System)** untuk memprediksi tingkat kerawanan atau indeks bahaya banjir berdasarkan parameter intensitas curah hujan dan tinggi muka air sungai secara interaktif.

---

## 2. Fitur Utama
1. **Peta Peringatan Real-Time BMKG (CAP Standard):**
   - Menampilkan poligon wilayah terdampak cuaca ekstrem secara langsung dari umpan (feed) XML CAP BMKG.
   - Menyediakan pencarian kecamatan terdampak (regex-based extraction) serta penyaringan berbasis provinsi.
   - Menyediakan instruksi keselamatan resmi dari BMKG untuk setiap jenis peringatan bencana.
2. **Visualisasi Cuaca & Isotherm Heatmap Nasional (Open-Meteo):**
   - Menampilkan visualisasi kondisi cuaca terkini (suhu, kelembapan, tekanan, tutupan awan, kecepatan, dan arah angin) di **15 kota besar** di seluruh Indonesia dari Sabang sampai Merauke secara batch (sekali request).
   - Menyertakan **Peta Isoterm/Heatmap Suhu** dinamis berbasis lingkaran warna desaturasi yang membaur di peta untuk memberikan sensasi peta radar cuaca nyata.
   - Menggunakan ikon cuaca FontAwesome dengan animasi goyang mikro (`bounceSlow`) dan jarum kompas arah angin yang berputar sesuai derajat angin real-time.
3. **Kontrol Layer Peta & Legenda:**
   - Panel kanan atas untuk menyalakan/mematikan visualisasi peringatan BMKG dan visualisasi cuaca Indonesia secara terpisah.
   - Panel kiri bawah menampilkan legenda tingkat keparahan bencana dan skala suhu wilayah.
4. **Bilingual Localization:**
   - Mendukung peralihan bahasa instan antara **Bahasa Indonesia (ID)** dan **English (EN)** pada seluruh teks antarmuka dan data peringatan.
5. **Simulator Logika Fuzzy (Mamdani/Tsukamoto):**
   - Memproses simulasi bahaya banjir menggunakan library `scikit-fuzzy` di backend Python.
   - Menampilkan tabel matriks evaluasi 9 aturan (rules) logika fuzzy yang menyala (highlighted) secara dinamis sesuai pergerakan slider input.
   - Dilengkapi dengan *radial gauge chart* modern yang merepresentasikan persentase Indeks Bahaya secara interaktif.

---

## 3. Metode & Basis Pengetahuan Sistem Pakar (Fuzzy Logic)
Metode Fuzzy Logic dipilih karena fenomena cuaca dan ketinggian air sungai tidak dapat dibatasi secara hitam-putih kaku (misalnya curah hujan 49 mm dinilai aman sedangkan 51 mm dinilai bahaya). Logika fuzzy memberikan transisi derajat keanggotaan (membership function) yang dinamis dan realistis.

### A. Fuzzifikasi (Input & Output)
Sistem mengevaluasi 2 variabel input dan menghasilkan 1 variabel output:
1. **Input 1: Curah Hujan (Rainfall Intensity)** [Semesta: 0 s.d 150 mm/hari]
   - *Ringan*: 0 - 50 mm
   - *Sedang*: 20 - 100 mm
   - *Lebat*: 80 - 150 mm
2. **Input 2: Tinggi Muka Air Sungai** [Semesta: 0 s.d 300 cm]
   - *Normal*: 0 - 100 cm
   - *Siaga*: 80 - 250 cm
   - *Bahaya*: 200 - 300 cm
3. **Output: Indeks Bahaya (Danger Index)** [Semesta: 0 s.d 100%]
   - *Aman (Safe)*: 0 - 30%
   - *Waspada (Caution)*: 20 - 60%
   - *Siaga (Warning)*: 50 - 90%
   - *Awas (Danger)*: 80 - 100%

### B. Matriks Aturan Evaluasi (9 Rules)
Otak inferensi fuzzy dibentuk oleh kombinasi 9 aturan berikut:
1. **Rule 1:** IF Hujan *Ringan* AND Tinggi Air *Normal* THEN Status *Aman*
2. **Rule 2:** IF Hujan *Ringan* AND Tinggi Air *Siaga* THEN Status *Waspada*
3. **Rule 3:** IF Hujan *Ringan* AND Tinggi Air *Bahaya* THEN Status *Siaga*
4. **Rule 4:** IF Hujan *Sedang* AND Tinggi Air *Normal* THEN Status *Waspada*
5. **Rule 5:** IF Hujan *Sedang* AND Tinggi Air *Siaga* THEN Status *Siaga*
6. **Rule 6:** IF Hujan *Sedang* AND Tinggi Air *Bahaya* THEN Status *Awas*
7. **Rule 7:** IF Hujan *Lebat* AND Tinggi Air *Normal* THEN Status *Siaga*
8. **Rule 8:** IF Hujan *Lebat* AND Tinggi Air *Siaga* THEN Status *Awas*
9. **Rule 9:** IF Hujan *Lebat* AND Tinggi Air *Bahaya* THEN Status *Awas*

### C. Defuzzifikasi
Evaluasi rules diproses di backend menggunakan library `scikit-fuzzy` dengan metode Mamdani/Tsukamoto untuk menghasilkan satu angka pasti (*crisp value*) persen Indeks Bahaya.

---

## 4. Arsitektur Teknologi
- **Backend:** Python 3 + Flask framework.
- **Data Caching:** Thread-safe in-memory cache dengan TTL 90 detik di backend untuk mencegah overload permintaan ke server BMKG (mematuhi batas maksimal 60 requests/min/IP).
- **Libraries:** `scipy`, `numpy`, `scikit-fuzzy`.
- **Map Engine:** Leaflet.js dengan basemap CartoDB Voyager.
- **Frontend/UI:** HTML5, Tailwind CSS, FontAwesome 6, dan Vanilla JavaScript (Asynchronous API Calls).

---

## 5. Cara Menjalankan Aplikasi Secara Lokal
1. Pastikan Python 3 sudah terinstal di komputer Anda.
2. Buat Virtual Environment dan instal dependensi:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Jalankan aplikasi Flask:
   ```bash
   python app.py
   ```
4. Buka browser dan buka alamat: `http://127.0.0.1:5000`

---

## 6. Panduan Penilaian Presentasi Kelompok
Untuk mendapatkan nilai maksimal berdasarkan kriteria penilaian RTM:
- **Kemampuan Menjelaskan (40%):** Jelaskan mengapa logika fuzzy lebih realistis dibandingkan if-else statis dalam studi kasus alam seperti banjir. Tunjukkan visualisasi 9 aturan fuzzy yang menyala dinamis di dashboard saat slider digeser.
- **Studi Kasus & Live Koding (30%):** Tunjukkan struktur kode sistem fuzzy di `app.py` serta kueri XML BMKG. Lakukan simulasi live dengan dosen atau audiens (misalnya meminta angka skenario curah hujan dan tinggi air acak).
- **Desain & Bahasa (30%):** Karena bahasa presentasi disarankan menggunakan Bahasa Inggris, antarmuka dashboard ini telah mendukung peralihan bahasa (ID/EN) secara penuh. Pastikan slide presentasi Anda selaras dengan terminologi yang ada di dashboard ini.