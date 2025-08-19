# AISGuard — офлайн-детектор аномалий AIS

Проект для анализа судоходных AIS-логов и выявления аномалий/спуфинга. Работает офлайн, интерфейс — CLI, отчёты — JSON и PNG.

## Возможности
- detect: анализ CSV с треками — флаги "телепортов", нереалистичных скоростей, нарушения порядка времени; опционально ML-скоринг аномалий
- parse: базовая проверка NMEA (!AIVDM/!AIVDO) — валидация checksum, сбор статистики
- convert: конвертация NMEA → CSV на основе `pyais` (позиционные типы 1/2/3 + обогащение статикой из типа 5)
- экспорт GeoJSON и KML для треков и инцидентов

## Установка
```bash
pip install -r requirements.txt
```

## Формат входного CSV для detect
Ожидаются колонки:
- `mmsi` (int)
- `lat` (float, WGS84)
- `lon` (float, WGS84)
- `sog` (float, knots) — можно оставить пустым, будет пересчитано по треку
- `cog` (float, degrees) — опционально
- `ts` (ISO 8601, например `2024-05-01T12:34:56Z`)

Опциональные (при конвертации через `convert`):
- `heading`, `nav_status`, `rot`
- `name`, `callsign`, `ship_type`, `dim_a`, `dim_b`, `dim_c`, `dim_d`

Пример: `aisguard/samples/sample.csv`

## Запуск
- Конвертация NMEA → CSV:
```bash
python -m aisguard.cli convert \
  --in aisguard/samples/sample.nmea \
  --out out/converted.csv \
  --start-ts 2024-05-01T00:00:00Z \
  --step-sec 2
```

- Анализ CSV (с графиком, GeoJSON и ML):
```bash
python -m aisguard.cli detect \
  --in aisguard/samples/sample.csv \
  --report out/report.json \
  --plot out/tracks.png \
  --geojson out/tracks.geojson \
  --kml out/tracks.kml \
  --max-speed 45 --max-jump 20 \
  --ml --ml-contamination 0.02
```

- Парсинг NMEA (валидность строк, агрегированная статистика):
```bash
python -m aisguard.cli parse --in aisguard/samples/sample.nmea --out out/raw_nmea.csv
```

## Выводы
- JSON-отчёт: список инцидентов и сводка по флагам
- PNG: график траекторий с подсветкой аномалий
- GeoJSON: линии треков (LineString) и точки инцидентов (Point)
- KML: LineString для треков и Placemarks для инцидентов

## Ограничения
- `convert` экспортирует только позиционные сообщения (типы 1/2/3). Для абсолютного времени используйте `--start-ts`.
- ML-скоринг (IsolationForest) работает как вспомогательная эвристика; возможны ложные срабатывания.

## Идеи для развития
- Полный декодер AIS-полей (pyais) и геопараметров из NMEA
- Модель аномалий (IsolationForest) по фичам траектории
- Экспорт GeoJSON/KML
