# 📄 Telemetry Log Formatı

Bu proje tarafından üretilen log dosyaları CSV formatındadır. Her satır bir telemetri örneğini temsil eder.

Aşağıdaki kolonlar bulunur:

| Kolon Adı            | Açıklama                         |
|----------------------|----------------------------------|
| `timestamp`          | UTC zaman damgası                |
| `altitude_m`         | İrtifa (metre)                   |
| `roll_deg`           | Roll açısı                       |
| `pitch_deg`          | Pitch açısı                      |
| `yaw_deg`            | Yaw açısı                        |
| `battery_remaining`  | Pil yüzdesi                      |
| `gps_fix`            | 1 = Fix var, 0 = Yok             |
| `gps_satellites`     | Uydu sayısı                      |
| `rssi`               | Bağlantı sinyal seviyesi (dBm)   |
| `flight_mode`        | Uçuş modu                        |


## 📌 Örnek Log Satırı

2025-12-06T17:31:40.123456,45.2,1.3,-0.7,180.4,98,1,10,-46,AUTO



## 🧱 Tasarım İlkeleri

Bu format:

- İnsan tarafından okunabilir
- Excel, MATLAB, Pandas ile direkt açılabilir
- Genişletilebilir  
  (örn. ivmeölçer verileri, motor RPM, RC komutları eklemeye uygun)


## 📦 Veri Tipi Eşlemesi

| Alan                           | Python Tipi          |
|--------------------------------|----------------------|
| timestamp                      | `datetime`           |
| altitude_m                     | `float`              |
| roll_deg / pitch_deg / yaw_deg | `float`              |
| battery_remaining              | `float`              |
| gps_fix                        | `bool`               |
| gps_satellites                 | `int`                |
| rssi                           | `float`              |
| flight_mode                    | `FlightMode` enum    |


## Format Kısıtları

- CSV virgül ayracına göre parse edilir  
- Bozuk satırlar parser tarafından güvenli şekilde atlanır  
- Zaman damgası ISO8601 formatındadır  
- Tüm sayısal alanlar SI birimleriyle gelir


Bu doküman hem simülasyon çıktısını inceleyen mühendislere hem de gerçek sensör verilerinden bu formata dönüştürme yapmak isteyenlere referans niteliğindedir.
