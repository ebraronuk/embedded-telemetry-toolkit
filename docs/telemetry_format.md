# Telemetry Log Format

Bu proje tarafından üretilen log dosyaları CSV formatındadır. Her satır, uçuş telemetrisinden tek bir örneği temsil eder.

## Kolonlar

| Kolon Adı                | Açıklama                               |
|--------------------------|----------------------------------------|
| `timestamp_utc`          | ISO8601 UTC zaman damgası              |
| `lat` / `lon`            | Enlem / boylam (derece)                |
| `altitude_m`             | İrtifa (metre, MSL)                    |
| `ground_speed_mps`       | Yatay hız (m/s)                        |
| `vertical_speed_mps`     | Düşey hız, tırmanış(+) / süzülüş(-)    |
| `roll_deg` / `pitch_deg` | Tutum açıları (derece)                 |
| `yaw_deg`                | Baş açısı (derece)                     |
| `flight_mode`            | Otomatik pilot modu                    |
| `armed`                  | Motor kilidi (1 = açık, 0 = kapalı)    |
| `battery_voltage`        | Pil gerilimi (V)                       |
| `battery_remaining_pct`  | Pil yüzdesi (%)                        |
| `gps_fix`                | 1 = Fix var, 0 = Yok                   |
| `satellites`             | Kullanılan uydu sayısı                 |
| `link_rssi`              | Veri linki RSSI (dBm)                  |

## RSSI Değerlerini Yorumlama

-40 dBm : Çok güçlü, saha testlerinde ideal seviye  
-70 dBm : Orta, çoğu görev için kabul edilebilir ancak marj sınırlı  
-90 dBm : Kritik, bağlantı kopma riski yüksek, failsafe tetiklenebilir

## Örnek Log Satırı

2025-12-06T17:31:40.123456,37.618820,-122.375400,118.5,12.3,0.4,3.2,1.1,182.5,AUTO,1,15.8,87.5,1,13,-46.7

## Tasarım İlkeleri

Bu format:

- İnsan tarafından okunabilir
- Excel, MATLAB, Pandas ile doğrudan açılabilir
- Genişletilebilir  
  (örn. ivmeölçer, motor RPM, RC komutları gibi alanlar eklemeye uygun)

## Veri Tipi Eşlemesi

| Alan                           | Python Tipi          |
|--------------------------------|----------------------|
| timestamp_utc                  | `datetime`           |
| lat / lon                      | `float`              |
| altitude_m                     | `float`              |
| ground_speed_mps               | `float`              |
| vertical_speed_mps             | `float`              |
| roll_deg / pitch_deg / yaw_deg | `float`              |
| flight_mode                    | `FlightMode` enum    |
| armed                          | `bool`               |
| battery_voltage                | `float`              |
| battery_remaining_pct          | `float`              |
| gps_fix                        | `bool`               |
| satellites                     | `int`                |
| link_rssi                      | `float`              |

## Format Kısıtları

- CSV virgül ayırıcı ile parse edilir  
- Bozuk satırlar parser tarafından güvenli şekilde atlanır  
- Zaman damgası ISO8601 formatındadır  
- Tüm sayısal alanlar SI birimleriyle gelir

Bu doküman hem simülasyon çıktısını inceleyen mühendislere hem de gerçek sensör verilerinden bu formata dönüştürme yapmak isteyenlere referans niteliğindedir.
