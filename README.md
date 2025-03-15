# Sustainability Metrics Monitoring

This application monitors system sustainability metrics, including CPU, GPU, and RAM power consumption, and estimates carbon emissions. It logs the data to a CSV file and exposes metrics to Prometheus for real-time monitoring.

## Features

- **Power Consumption Monitoring**: Tracks CPU, GPU, and RAM power usage.
- **Carbon Emissions Estimation**: Calculates emissions based on energy consumption and grid carbon factor.
- **Cloud Environment Detection**: Identifies if the system is running on AWS, Azure, or GCP.
- **Location Detection**: Fetches approximate latitude and longitude of the machine.
- **Prometheus Integration**: Exposes metrics for real-time monitoring.
- **CSV Logging**: Optionally logs metrics to a CSV file.

## Requirements

- Python 3.6 or higher
- Prometheus Client Library (`prometheus_client`)
- `psutil` for system monitoring
- `requests` for API calls
- Optional: `pynvml` for NVIDIA GPU monitoring

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd Sustainability
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. (Optional) Install `pynvml` for GPU monitoring:
   ```bash
   pip install nvidia-ml-py3
   ```

## Usage

1. Start the Prometheus HTTP server and begin monitoring:
   ```bash
   python app.py
   ```

2. Access Prometheus metrics at:
   ```
   http://localhost:9271/metrics
   ```

3. (Optional) Enable CSV logging by setting `write_to_file = True` in the script.

## Configuration

- **Grid Carbon Factor**: Update the `GRID_CARBON_FACTOR` constant to match your region's carbon intensity (default: 400 gCO2e/kWh).
- **CSV File Name**: Change the `CSV_FILE` constant to specify a different file name for logging.

## Metrics

### Numeric Metrics
The following metrics are exposed to Prometheus:
- `duration`: Monitoring duration (seconds)
- `emissions`: Carbon emissions (kgCO2e)
- `emissions_rate`: Emissions rate (kg/s)
- `cpu_power`: CPU power usage (Watts)
- `gpu_power`: GPU power usage (Watts)
- `ram_power`: RAM power usage (Watts)
- `cpu_energy`: CPU energy consumption (kWh)
- `gpu_energy`: GPU energy consumption (kWh)
- `ram_energy`: RAM energy consumption (kWh)
- `energy_consumed`: Total energy consumption (kWh)

### Text Labels
Metadata labels include:
- `project_name`, `country_name`, `region`, `cloud_provider`, `os`, `cpu_model`, `gpu_model`, etc.

## Stopping the Application

Press `Ctrl+C` to stop monitoring. If GPU monitoring is enabled, the script will automatically shut down NVML.

## Notes

- Ensure the system has internet access for location and cloud provider detection.
- GPU monitoring is only available for NVIDIA GPUs with NVML support.
- Prometheus must be configured to scrape metrics from `http://localhost:9271/metrics`.

