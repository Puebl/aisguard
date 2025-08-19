# AISGuard — офлайн-детектор аномалий AIS

Проект для анализа судоходных AIS-логов и выявления аномалий/спуфинга. Работает офлайн, интерфейс — CLI, отчёты — JSON и PNG.

## Возможности (MVP)
- detect: анализ CSV с треками — флаги "телепортов", нереалистичных скоростей, др.
- parse: базовая проверка NMEA (!AIVDM/!AIVDO) — валидация checksum, сбор статистики (без полного декодирования payload)

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

Пример: `aisguard/samples/sample.csv`

## Запуск
- Анализ CSV:
```bash
python -m aisguard.cli detect --in aisguard/samples/sample.csv --report out/report.json --plot out/tracks.png --max-speed 45 --max-jump 20
```

- Парсинг NMEA (валидность строк, агрегированная статистика):
```bash
python -m aisguard.cli parse --in data/sample.nmea --out out/raw_nmea.csv
```

## Выводы
- JSON-отчёт: список инцидентов и сводка по флагам
- PNG: график траекторий с подсветкой аномалий

## Ограничения MVP
- parse не выполняет полный AIS-декод (гео/скорость из payload); для детекции используйте готовые CSV или конвертеры сторонних источников.
- Детектор эвристический, без ML. Возможны ложные срабатывания.

## Идеи для развития
- Полный декодер AIS-полей (pyais) и геопараметров из NMEA
- Модель аномалий (IsolationForest) по фичам траектории
- Экспорт GeoJSON/KML
