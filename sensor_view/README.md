# Sensor Data Viewer

Standalone Python UI to browse and export data from `sensor_data.db`.

## Run

```bash
cd sensor_view
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

## Notes

- Select a DB file and load metadata.
- Choose time range and sensor IDs, then plot.
- Export CSV from the plotted data.
