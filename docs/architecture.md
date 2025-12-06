# Sistem Mimarisi

Bu proje, tipik bir yer istasyonu telemetri boru hattının sadeleştirilmiş bir modelidir. Veri akışı dört temel aşamada ilerler:

Simülatör → CSV Log → Parser → Analyzer → GUI/CLI

Modüler mimari sayesinde her bileşen kendi sorumluluğu içinde kalır ve ortak veri modeli üzerinden iletişim kurar.

## 1. Telemetry Data Model

`TelemetrySample` sınıfı bir UAV telemetri satırını temsil eder.

İçerdiği ana alanlar:

- Zaman damgası (UTC)
- İrtifa (m)
- Roll / pitch / yaw (tutum)
- Batarya yüzdesi
- GPS fix durumu ve uydu sayısı
- RSSI (dBm)
- Flight mode

Bu model:

- Parser tarafından üretilir  
- Analyzer tarafından tüketilir  
- Simülatör tarafından oluşturulur  

## 2. 🛫 UAV Telemetry Simulator

`UAVTelemetrySimulator` uçuş benzeri telemetri üretir:

- Süre ve frekans ayarlı simülasyon
- Gürültülü irtifa profili
- Pil tüketimi
- RSSI zayıflaması
- GPS değişkenliği
- Flight mode geçişleri (MANUAL → AUTO → RTL)

Çıktı formatı: **CSV (logs klasörüne)**

Amaç: Gerçek donanım olmadan uçtan uca telemetri zincirini test etmek.

## 3. Telemetry Parser

`UAVTelemetryParser` şu işlevleri sağlar:

- CSV dosyasını satır satır okur
- Her satırı `TelemetrySample` nesnesine dönüştürür
- Hatalı satırları güvenli şekilde atlar
- Eksik veri varsa toleranslı davranır

Parser, veri boru hattının **normalize etme** katmanıdır.

## 4. Telemetry Analyzer

`TelemetryAnalyzer` uçuş sonrası değerlendirme motorudur.

Analiz ettiği başlıklar:

- Pil tüketim davranışı
- GPS uygunluğu (fix, satellite)
- Tutum sapmaları (roll/pitch limit, yaw spike)
- Link sağlığı (RSSI)
- Mod geçiş tutarlılığı

Çıktı: **Anomali JSON raporu + severity derecesi**


## 5. Streamlit GUI

Kullanıcı arayüzü tüm pipeline aşamalarını görsel olarak yönetir:

- Simülasyon üretme
- Hazır log yükleme
- Ayrıştırma
- Anomali analizi
- Grafikleme (irtifa, pil, RSSI)

Test mühendislerinin saha öncesi doğrulama yapması için uygundur.


## 6. CLI Araçları

İki komut satırı aracı bulunur:

### `simulate.py`
CSV log üretir:
    python -m src.cli.simulate --duration 60

### `analyze.py`
Log dosyasını analiz eder:
    python -m src.cli.analyze logs/simulated_flight.log


CLI, hızlı otomasyon testleri için idealdir.


## 7. Modülerlik İlkesi

Her dosya yalnızca kendi sorumluluğunu içerir:

- Veri modeli → `schemas.py`
- Üretim → `simulator.py`
- Ayrıştırma → `parser.py`
- Analiz → `analyzer.py`
- Sunum → Streamlit GUI / CLI

Bu yaklaşım savunma projelerinde tercih edilen **temiz katmanlı mimarinin** bir örneğidir.
