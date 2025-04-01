import psutil
import os
import subprocess
import shutil

def get_total_power():
    """Fetch total system-wide power usage (CPU, GPU, ANE) using powermetrics."""
    if not shutil.which("powermetrics"):
        return None

    try:
        result = subprocess.run(
            ["sudo", "powermetrics", "--samplers", "cpu_power,gpu_power,ane_power", "--duration", "1"],
            capture_output=True, text=True
        )

        cpu_power, gpu_power, ane_power = 0, 0, 0
        
        for line in result.stdout.split("\n"):
            if "CPU Power" in line:
                cpu_power = float(line.split(':')[1].strip().split()[0])
            elif "GPU Power" in line:
                gpu_power = float(line.split(':')[1].strip().split()[0])
            elif "ANE Power" in line:
                ane_power = float(line.split(':')[1].strip().split()[0])

        return {
            "CPU Power (mW)": cpu_power,
            "GPU Power (mW)": gpu_power,
            "ANE Power (mW)": ane_power,
            "Total Power (mW)": cpu_power + gpu_power + ane_power
        }
    except Exception as e:
        print("Error fetching power metrics:", e)
        return None

def list_running_processes():
    """List all running processes with their PID and status."""
    print("\n%-10s %-30s %-15s" % ("PID", "Process Name", "Status"))
    print("-" * 60)
    
    for process in psutil.process_iter(attrs=['pid', 'name', 'status']):
        try:
            print("%-10s %-30s %-15s" % (process.info['pid'], process.info['name'], process.info['status']))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

def get_power_consumption():
    """Fetch real-time power consumption using powermetrics (macOS)."""
    try:
        if os.path.exists("/sys/class/powercap/intel-rapl"):  # Intel RAPL check (Linux)
            with open("/sys/class/powercap/intel-rapl:0/energy_uj", "r") as f:
                energy_uj = int(f.read().strip())
                power_watts = energy_uj / 1e6  # Convert microjoules to watts
                return round(power_watts, 2)
        elif shutil.which("ipmitool"):  # Check if IPMI tool is available (Servers)
            result = subprocess.run(["ipmitool", "sensor"], capture_output=True, text=True)
            for line in result.stdout.split("\n"):
                if "Power" in line:
                    parts = line.split('|')
                    return round(float(parts[1].strip()), 2)
        elif shutil.which("powermetrics"):  # Check if powermetrics is available (macOS)
            power_data = get_total_power()
            if power_data:
                return round(power_data["Total Power (mW)"] / 1000, 2)  # Convert mW to W
    except Exception as e:
        print("Error fetching power consumption:", e)
        return None
    return None

def estimate_power_usage(requests_per_second=30000):
    """Estimate power consumption based on typical data center metrics."""
    watts_per_request = 0.0002  # Approximate power usage per request in watts
    return round(requests_per_second * watts_per_request, 2)

def estimate_facility_power(it_equipment_power, pue=1.5):
    """Estimate total facility power consumption using PUE (Power Usage Effectiveness)."""
    return round(it_equipment_power * pue, 2)

def get_process_details(pid, total_facility_power=None, it_equipment_power=None):
    """Get process details including power estimation and PUE calculation."""
    try:
        process = psutil.Process(pid)
        cpu_usage = process.cpu_percent(interval=1)  # Get CPU usage over 1 second
        memory_usage = process.memory_info().rss  # Resident Set Size (RAM usage)
        real_power = get_power_consumption()
        estimated_it_power = estimate_power_usage(30000)  # Assuming 30K requests/sec
        estimated_total_power = estimate_facility_power(estimated_it_power)

        print("\n🔍 Details of PID:", pid)
        print("📌 Name:", process.name())
        print("📌 Status:", process.status())
        print("📌 CPU Usage:", cpu_usage, "%")
        print("📌 Memory Usage:", memory_usage, "bytes")
        print("📌 Threads:", process.num_threads())

        if real_power:
            print("\n⚡ Real-time Power Consumption:", real_power, "Watts")
        else:
            print("\n⚡ Estimated IT Equipment Power Consumption for 30K RPS:", estimated_it_power, "Watts")
            print("⚡ Estimated Total Facility Power Consumption:", estimated_total_power, "Watts")

        if total_facility_power and it_equipment_power:
            pue = total_facility_power / it_equipment_power
            print("\n🏢 Power Usage Effectiveness (PUE):", round(pue, 2))
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        print("⚠ Process not found or access denied.")

if __name__ == "__main__":
    list_running_processes()
    try:
        pid = int(input("\nEnter PID to get more details: "))
        
        # Default estimated values
        estimated_it_power = estimate_power_usage(30000)
        estimated_total_power = estimate_facility_power(estimated_it_power)
        
        # Prompt for optional user input
        total_facility_power_input = input("Enter total facility power consumption (in Watts) (or press Enter to use default): ")
        it_equipment_power_input = input("Enter IT equipment power consumption (in Watts) (or press Enter to use default): ")

        total_facility_power = float(total_facility_power_input) if total_facility_power_input else estimated_total_power
        it_equipment_power = float(it_equipment_power_input) if it_equipment_power_input else estimated_it_power

        get_process_details(pid, total_facility_power, it_equipment_power)
    except ValueError:
        print("❌ Invalid input entered. Please enter numeric values.")
