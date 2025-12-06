# 🛰️ **Embedded Telemetry Toolkit**
### *UAV Telemetri Simülasyonu, Ayrıştırması ve Uçuş Sonrası Analizi için Modüler Python Kütüphanesi*

Bu çalışma, insansız hava araçlarından elde edilen telemetri verilerinin **üretimi, ayrıştırılması ve analizine yönelik uçtan uca bir test altyapısı** oluşturmak amacıyla geliştirilmiştir.  
Gerçek donanım olmadan, kontrollü bir simülasyon ortamında **uçuş verisi işleme zincirinin tüm adımlarını** inceleme ve doğrulama imkânı sağlar.

Savunma ve havacılık projelerinde telemetri; sistem sağlığı takibi, uçuş emniyeti, sensör doğrulama ve görev analizlerinde temel veri kaynağıdır.  
Bu proje, hem **entegrasyon mantığını güçlendirmek** hem de **uçuş veri boru hattını uçtan uca kavramak** için oluşturulmuş modüler bir çalışma ortamıdır.

---

#  **Ana Bileşenler**

Proje, gerçek bir yer istasyonu mimarisine benzer şekilde dört çekirdek modül üzerine kuruludur:

- **Telemetri Veri Modeli**  
  Uçuş pozisyonu, tutum, güç sistemi, GPS ve link sağlık bilgilerini temsil eden sade bir veri şeması.

- **Uçuş Telemetri Simülatörü**  
  Gerçekçi hareket profilleri ve sensör davranışlarıyla CSV formatında uçuş log’u üretir.

- **Telemetri Ayrıştırıcısı (Parser)**  
  Üretilen log dosyalarını `TelemetrySample` nesnelerine dönüştürür.

- **Uçuş Sonrası Analiz Modülü (Analyzer)**  
  Batarya düşüşü, GPS kaybı, attitude bozuklukları, RSSI zayıflığı ve mod geçiş hataları gibi temel anormallikleri tespit eder.

---

#  **Sistem Mimarisi**

Aşağıdaki şema, veri akışını ve modüller arası ilişkiyi göstermektedir:

            ┌──────────────────────────┐
            │   Uçuş Telemetri         │
            │      Simülatörü          │
            │  (simulator.py)          │
            └─────────────┬────────────┘
                         CSV
                          │
                          ▼
               ┌──────────────────────┐
               │   Telemetri Parser   │
               │    (parser.py)       │
               └──────────────┬───────┘
                              │
                     TelemetrySample listesi
                              │
                              ▼
                  ┌────────────────────┐
                  │   Uçuş Sonrası     │
                  │      Analiz        │
                  │   (analyzer.py)    │
                  └──────────────┬─────┘
                                 │
                        Anomali Raporu
                                 │
                                 ▼
                          CLI Arayüzleri
                 (simulate.py / analyze.py)

Sade ve genişletilebilir bir yapı tercih edilmiştir.  
Her modül kendi sorumluluğu içinde kalır; ortak veri modeli üzerinden iletişim kurulur.

---

#  **Kurulum**

cd embedded-telemetry-toolkit
pip install -r requirements.txt


Proje Python 3.10+ ile test edilmiştir.

---

# 🛫 **Uçuş Telemetri Simülasyonu (CLI)**

Aşağıdaki komut bir dakikalık uçuş simülasyonu oluşturur:

    python -m src.cli.simulate --duration 60

Varsayılan çıktı dosyası: logs/simulated_flight.log
Örnek bir başarı mesajı: Simülasyon tamamlandı: logs/simulated_flight.log


İsteğe bağlı parametreler:
--frequency Telemetri üretim frekansı (Hz)
--output Özel log dosyası adı


---

# 🛰️ **Telemetri Analizi (CLI)**

Üretilen uçuş log’u analiz etmek için:

    python -m src.cli.analyze logs/simulated_flight.log


Örnek çıktı:Batarya:

Yok
GPS:

GPS anomaly at 2025-12-06T16:53:20

GPS anomaly at 2025-12-06T16:53:24
Tutum:

Yok
RSSI:

Yok
Flight Mode:

Yok


---

# **Streamlit GUI**

Streamlit arayüzü, telemetriyi uçtan uca yönetmek için tasarlandı: sol panelden simülasyon süresi ve frekansı ayarlanır, tek tıkla yeni log üretilir veya hazır bir log yüklenir; ardından ayrıştırma, analiz ve grafikleme ardışığı otomatik çalışır. Amaç, saha öncesi hızlı deneme ve anomali görünürlüğü sağlamaktır.

Kullanıcı akışı: **Simülasyon** sekmesinde CSV üretme/yükleme, **Analiz** sekmesinde özet ve anomali JSON’u, **Grafikler** sekmesinde zaman serileri, **Anomali Karnesi** sekmesinde kategori bazlı listeler. Pipeline net: **Simülasyon → Ayrıştırma → Analiz → Grafikler**.

Önemli grafikler: (1) İrtifa vs Zaman — görev profili ve stabiliteyi okumak için. (2) Batarya Yüzdesi vs Zaman — iniş için enerji yeterliliğini görmek için. (3) RSSI vs Zaman — yer istasyonu link sağlığını takip etmek için.


## Kullanım Örneği (Ekran Görüntüleri)
Arayüzün tam kullanım akışı için `docs/usage_demo/` klasörüne bakabilirsiniz.

- Simülasyon başlatma
- Analiz özeti
- Grafikleme ekranları
- Anomali Karnesi

## GUI Nasıl Başlatılır?
Streamlit tabanlı grafik arayüzü başlatmak için proje klasöründe aşağıdaki komutu çalıştırın:

  streamlit run streamlit_app.py

Arayüz tarayıcıda otomatik olarak şu adreste açılır:

  http://localhost:8501

Eğer streamlit komutu tanınmazsa şu alternatif komutu kullanabilirsiniz:

  python -m streamlit run streamlit_app.py

---
## 🧭 Anomali Analizi Mantığı

Uçuş sonrası analiz modülü, telemetri verilerini tarayarak belirli eşiklere ve davranış modellerine göre anomali tespiti yapar. Tespit edilen tüm anormallikler kategori bazlı olarak **Anomali Karnesi** sekmesinde gösterilir.

---

## ⚡ 1. Batarya Anomalileri

Aykırı enerji tüketimi veya kritik seviyeler:

- **Hızlı tüketim:**  
  Birkaç saniyelik pencerede pil yüzdesi belirli bir orandan fazla düşerse.
- **Kritik pil seviyesi:**  
  `battery_remaining < 20%`
- **Gerilim düşüşü kaynaklı çökme işareti** *(ileride eklenecek)*

---

## 📡 2. GPS Anomalileri

Konumlama ve navigasyon bozuklukları:

- **GPS fix yok:**  
  `fix_status == 0`
- **Uydu sayısı yetersiz:**  
  `satellites < 6`
- **Konum atlaması / jitter** *(ileride eklenecek)*

---

## 🎛️ 3. Tutum (Attitude) Anomalileri

Araç dengesini etkileyen durumsal bozulmalar:

- **Roll / pitch limit aşımı:**  
  `abs(roll) > 35°` veya `abs(pitch) > 35°`
- **Ani yaw sıçraması:**  
  `|yaw(t) - yaw(t-1)| > 45°/s`

---

## 📶 4. RSSI Anomalileri

Yer istasyonu ile bağlantı sağlığını ifade eder:

- **Kritik link seviyesi:**  
  `rssi < -90 dBm`
- **Sürekli düşen trend:**  
  Arka arkaya n noktada lineer düşüş gözlenirse.

---

## 🛩️ 5. Flight Mode Anomalileri

Görev akışına aykırı mod geçişleri:

- “Auto → Manual → Auto” gibi hızlı, tutarsız geçiş dizileri  
- Beklenmeyen acil durum modu

---

## 🎚️ Genel Severity (Ciddiyet) Hesabı

Analyzer tüm kategorilerde bulguları değerlendirir ve bir toplam ciddiyet sınıfı üretir:

- **⛔ high:**  
  `≥ 2 kritik anomali`
- **⚠️ medium:**  
  `1 kritik + birkaç orta seviye`
- **ℹ️ low:**  
  Küçük sapmalar veya sınıra yakın durumlar

#  **Projenin Öğrenme Kazanımları**

Bu çalışma, uçuş sistemlerinde sık karşılaşılan bazı kavramları gerçekçi ancak erişilebilir bir örnekle somutlaştırır:

- Telemetri formatı ve sensor veri yapılarının modellenmesi  
- Uçuş profili, pozisyon ve attitude simülasyonu  
- CSV tabanlı log yapıları  
- Veri ayrıştırma ve hata toleransı  
- Uçuş sonrası analiz teknikleri  
- Modüler Python mimarisi  
- Savunma projelerinde sık kullanılan uçtan uca veri boru hattı yaklaşımı  

---

#  **Neden Bu Proje?**

Bu proje, profesyonel bir ürün geliştirme amacı taşımayan;  
ancak **sistem düşüncesi, entegrasyon mantığı ve telemetri analitiği** gibi konularda deneyim kazanmak için hazırlanmış bir çalışma ortamıdır.

Savunma sanayiinde çalışan mühendislerin büyük bölümü,  
telemetri zincirinin (üretim → kaydetme → ayrıştırma → analiz)  
en az bir aşamasıyla mutlaka çalışır.

Bu proje, bu sürecin tamamına hakim olmayı hedefleyen sade bir teknik egzersizdir.

---

# **Gelecek Geliştirmeler**

- Gerçek IMU/GPS log’larıyla karşılaştırma testleri  
- Basit görsel arayüz (Flask/Streamlit)  
- Telemetri zaman serisi grafiklerinin üretilmesi  
- ROS bag export  
- Anomali sınıflandırma modeli  
- Çoklu uçuş karşılaştırma desteği  

---

#  **Lisans**

MIT Lisansı.

---

#  **Son Not**

Bu proje, telemetri/veri işleme alanında pratik bir temel oluşturmak ve kendi öğrenme sürecimi pekiştirmek amacıyla hazırlanmıştır.  
Modüler yapısı sayesinde farklı telemetri kaynaklarına veya sistem test senaryolarına kolayca uyarlanabilir.
