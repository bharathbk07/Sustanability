import os
import csv
import time
import psutil
import platform
import requests
from datetime import datetime
from uuid import uuid4
import subprocess
from prometheus_client import Gauge, start_http_server, CollectorRegistry

# Try importing NVML for GPU monitoring (Only available for NVIDIA GPUs)
gpu_available = False
is_apple_silicon = platform.system() == "Darwin" and platform.machine() in ["arm64", "aarch64"]
write_to_file = False
# Headers
HEADERS = [
    "timestamp", "project_name", "run_id", "duration", "emissions", "emissions_rate",
    "cpu_power", "gpu_power", "ram_power", "cpu_energy", "gpu_energy", "ram_energy",
    "energy_consumed", "country_name", "country_iso_code", "region", "on_cloud",
    "cloud_provider", "cloud_region", "os", "python_version", "cpu_count", "cpu_model", "cpu_name",
    "gpu_count", "gpu_model", "gpu_name", "longitude", "latitude", "ram_total_size", "ram_name", "tracking_mode"
]

# ✅ List of Numeric Metrics
NUMERIC_METRICS = [
    "duration", "emissions", "emissions_rate", "cpu_power", "gpu_power", "ram_power",
    "cpu_energy", "gpu_energy", "ram_energy", "energy_consumed", "cpu_count", "gpu_count", "ram_total_size"
]

# ✅ List of Text Fields (stored as labels)
TEXT_LABELS = [
    "project_name", "country_name", "country_iso_code", "region", "on_cloud",
    "cloud_provider", "cloud_region", "os", "python_version", "cpu_model", "cpu_name",
    "gpu_model", "gpu_name", "longitude", "latitude", "ram_name", "tracking_mode"
]

# ✅ Use a Registry to prevent duplicate registration
registry = CollectorRegistry()

# ✅ Create Gauges for numeric metrics
metrics = {
    metric: Gauge(f"sustainability_{metric}", f"Metric for {metric}", registry=registry)
    for metric in NUMERIC_METRICS
}

# ✅ Create a single Gauge for text labels (stored as metadata)
info_metric = Gauge(
    "sustainability_info",
    "Metadata labels for sustainability metrics",
    labelnames=TEXT_LABELS,
    registry=registry
)


if not is_apple_silicon:
    try:
        from pynvml import (
            nvmlInit,
            nvmlDeviceGetHandleByIndex,
            nvmlDeviceGetPowerUsage,
            nvmlShutdown,
            nvmlSystemGetDriverVersion,
        )
        nvmlInit()  # Initialize NVIDIA GPU monitoring
        gpu_available = True
    except Exception as e:
        print(f"Warning: Could not initialize NVML for GPU monitoring. Reason: {e}")
        gpu_available = False

# Constants
GRID_CARBON_FACTOR = 400  # gCO2e/kWh (Change as per country)
PROJECT_NAME = "codecarbon"
CSV_FILE = "sustainability_metrics.csv"

# Function to detect cloud provider
def get_cloud_info():
    """Detects if running on AWS, Azure, or GCP."""
    cloud_provider, cloud_region = "N", "N/A"
    
    try:
        if os.path.exists("/sys/hypervisor/uuid") and "ec2" in open("/sys/hypervisor/uuid").read():
            cloud_provider = "aws"
            cloud_region = requests.get("http://169.254.169.254/latest/meta-data/placement/region", timeout=2).text
        elif "Microsoft" in platform.uname().release:
            cloud_provider = "azure"
            cloud_region = "brazilsouth"  # Azure does not expose this directly
        elif os.path.exists("/etc/google_system"):
            cloud_provider = "gcp"
            cloud_region = requests.get(
                "http://metadata.google.internal/computeMetadata/v1/instance/zone", 
                headers={"Metadata-Flavor": "Google"}, 
                timeout=2
            ).text.split("/")[-1]
    except Exception as e:
        print(f"Warning: Could not determine cloud provider. Reason: {e}")
    
    return cloud_provider, cloud_region

# Function to get location
def get_location():
    """Fetches the approximate latitude and longitude of the machine."""
    try:
        response = requests.get("http://ip-api.com/json/", timeout=3).json()
        return response["country"], response["countryCode"], response["regionName"], response["lat"], response["lon"]
    except Exception as e:
        print(f"Warning: Could not fetch location data. Reason: {e}")
        return "Unknown", "N/A", "N/A", "N/A", "N/A"

def get_system_info():
    """Retrieves detailed system information including CPU, GPU, RAM, and OS details."""
    # Get CPU model and count
    cpu_model = platform.processor() or "Unknown CPU"
    cpu_count = psutil.cpu_count(logical=True)

    # Get OS and Python version
    os_info = f"{platform.system()}-{platform.version()}"
    python_version = platform.python_version()

    # Get total RAM size in GB
    ram_total_size = round(psutil.virtual_memory().total / (1024 ** 3), 2)  # Convert bytes to GB

    # Getting CPU Name
    cpu_name = "Unknown"
    try:
        if platform.system() == "Windows":
            cpu_name = subprocess.check_output("wmic cpu get Name", shell=True).decode().split("\n")[1].strip()
        elif platform.system() == "Darwin":  # macOS
            cpu_name = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"]).decode().strip()
        elif platform.system() == "Linux":
            with open("/proc/cpuinfo", "r") as f:
                for line in f.readlines():
                    if "model name" in line:
                        cpu_name = line.split(":")[1].strip()
                        break
    except Exception as e:
        print(f"Warning: Could not fetch CPU name. Reason: {e}")

    # GPU info (Only if available)
    gpu_count = 0
    gpu_model = "N/A"
    gpu_name = "Unknown"

    try:
        if platform.system() == "Windows":
            gpu_name = subprocess.check_output("wmic path win32_videocontroller get name", shell=True).decode().split("\n")[1].strip()
            gpu_count = 1  # Assuming at least one GPU
        elif platform.system() == "Darwin":
            gpu_name = subprocess.check_output(["system_profiler", "SPDisplaysDataType"]).decode()
            for line in gpu_name.split("\n"):
                if "Chipset Model:" in line:
                    gpu_name = line.split(":")[1].strip()
                    gpu_count = 1
                    break
        elif platform.system() == "Linux":
            try:
                gpu_name = subprocess.check_output("lspci | grep VGA", shell=True).decode().split(":")[-1].strip()
                gpu_count = 1
            except:
                gpu_name = "Unknown GPU"
    except Exception as e:
        print(f"Warning: Could not fetch GPU details. Reason: {e}")

    # Getting RAM Name (Manufacturer)
    ram_name = "Generic RAM"
    try:
        if platform.system() == "Windows":
            ram_name = subprocess.check_output("wmic memorychip get Manufacturer", shell=True).decode().split("\n")[1].strip()
        elif platform.system() == "Linux":
            ram_name = subprocess.check_output("sudo dmidecode --type 17 | grep 'Manufacturer'", shell=True).decode().split("\n")[0].split(":")[1].strip()
    except Exception as e:
        print(f"Warning: Could not fetch RAM name. Reason: {e}")

    return cpu_model, cpu_count, cpu_name, gpu_model, gpu_count, gpu_name, ram_total_size, ram_name, os_info, python_version

# Function to calculate power consumption
def get_power_metrics():
    """Estimates CPU, GPU, and RAM power usage and calculates emissions."""
    cpu_usage = psutil.cpu_percent(interval=1)
    cpu_power = (cpu_usage / 100) * 65  # Approximate CPU max power consumption

    gpu_power = 0
    if gpu_available:
        try:
            handle = nvmlDeviceGetHandleByIndex(0)
            gpu_power = nvmlDeviceGetPowerUsage(handle) / 1000  # Convert to Watts
        except Exception as e:
            print(f"Warning: Could not fetch GPU power usage. Reason: {e}")
            gpu_power = 0

    ram_power = psutil.virtual_memory().used / (1024 ** 3) * 2  # Approx 2W per GB

    # Calculate energy consumption (kWh)
    duration_hours = 1 / 3600  # 1-second interval converted to hours
    cpu_energy = (cpu_power * duration_hours) / 1000
    gpu_energy = (gpu_power * duration_hours) / 1000
    ram_energy = (ram_power * duration_hours) / 1000
    energy_consumed = cpu_energy + gpu_energy + ram_energy

    # Carbon Emissions (gCO2e)
    emissions = energy_consumed * GRID_CARBON_FACTOR / 1000  # Convert to kgCO2e
    emissions_rate = emissions / 1  # kg/s

    return cpu_power, gpu_power, ram_power, cpu_energy, gpu_energy, ram_energy, energy_consumed, emissions, emissions_rate

def save_to_csv(data):
    """Writes sustainability metrics to a CSV file and sends data to Prometheus."""
    csv_file = "sustainability_metrics.csv"
    
    # Check if the file exists, else create a new file with headers
    if not os.path.isfile(csv_file):
        with open(csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(HEADERS)  # Write headers for a new file

    # Append data to the file
    with open(csv_file, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(data)

def send_to_prometheus(data):
    """Sends numeric metrics and text labels to Prometheus."""
    labels = {}
    
    for i, value in enumerate(data):
        header = HEADERS[i]
        
        # ✅ Store numeric metrics
        if header in NUMERIC_METRICS:
            try:
                metrics[header].set(float(value))
            except ValueError:
                print(f"Warning: Skipping non-numeric value for {header}: {value}")

        # ✅ Store text fields as labels
        elif header in TEXT_LABELS:
            labels[header] = str(value)

    # ✅ Update the info metric with labels
    info_metric.labels(**labels).set(1)  # A constant value (1) to register labels

# Main Function
def main():
    """
    Main loop that collects and logs sustainability metrics every second.
    
    - Detects cloud environment and location.
    - Monitors CPU, GPU, and RAM power consumption.
    - Estimates carbon emissions.
    - Saves results to a CSV file.
    """
    print("Monitoring Sustainability Metrics... (Press Ctrl+C to stop)")
    
    cloud_provider, cloud_region = get_cloud_info()
    country_name, country_iso_code, region, latitude, longitude = get_location()
    cpu_model, cpu_count, cpu_name, gpu_model, gpu_count, gpu_name, ram_total_size, ram_name, os_info, python_version = get_system_info()
    
    try:
        while True:
            timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
            run_id = str(uuid4())[:8]
            duration = 1  # In seconds
            
            power_metrics = get_power_metrics()
            data = [
                timestamp, PROJECT_NAME, run_id, duration, *power_metrics,
                country_name, country_iso_code, region, "Y" if cloud_provider != "N" else "N",
                cloud_provider, cloud_region, os_info, python_version, cpu_count, cpu_model, cpu_name,
                gpu_count, gpu_model, gpu_name, longitude, latitude, ram_total_size, ram_name, "machine"
            ]
            
            if write_to_file:
                save_to_csv(data)
            # Send data to Prometheus
            send_to_prometheus(data)

            print(f"Logged sustainability metrics at {timestamp}")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nMonitoring stopped. Metrics saved in", CSV_FILE)
    finally:
        if gpu_available:
            nvmlShutdown()

if __name__ == "__main__":
    # Start Prometheus HTTP server on port 9271
    start_http_server(9271, registry=registry)
    main()
