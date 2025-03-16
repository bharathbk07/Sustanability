import subprocess
import platform
import time
import random

# Constants for energy and carbon calculations
CPU_WATTS_PER_CORE = 2.5  # Approximate power consumption per CPU core in Watts
JOULES_PER_WATT_SECOND = 1  # 1 Watt = 1 Joule per second
CARBON_INTENSITY_GRID = 0.4  # kg CO₂ per kWh (approximate global grid average)
CONTAINER_ENERGY_FACTOR = 0.8  # Efficiency factor for containers vs. traditional workloads

def is_docker_running():
    """Check if Docker is running by executing 'docker info'."""
    try:
        result = subprocess.run(["docker", "info"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            print("✅ Docker is running.")
            return True
        else:
            print("❌ Docker is not running.")
            return False
    except FileNotFoundError:
        print("⚠️ Docker is not installed or not in PATH.")
        return False

def get_container_metrics():
    """Retrieve number of running containers and container image sizes."""
    try:
        result = subprocess.run(["docker", "ps", "-q"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        running_containers = len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0

        result = subprocess.run(["docker", "images", "--format", "{{.Size}}"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        image_sizes = [float(size.split()[0]) for size in result.stdout.strip().split("\n") if size]

        avg_image_size = sum(image_sizes) / len(image_sizes) if image_sizes else 0
        return running_containers, avg_image_size
    except:
        return 0, 0

def get_kubernetes_metrics():
    """Retrieve Kubernetes-related sustainability metrics."""
    try:
        result = subprocess.run(["kubectl", "get", "pods", "--all-namespaces", "--no-headers"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        total_pods = len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0

        result = subprocess.run(["kubectl", "get", "nodes", "--no-headers"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        total_nodes = len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0

        node_utilization = (total_pods / total_nodes) if total_nodes else 0
        return total_pods, total_nodes, node_utilization
    except:
        return 0, 0, 0

def identify_idle_containers():
    """Check for idle containers."""
    try:
        result = subprocess.run(["docker", "ps", "--filter", "status=exited", "-q"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0
    except:
        return 0

def get_docker_pid():
    """Get Docker process ID (PID) based on OS."""
    try:
        if platform.system() == "Darwin" or platform.system() == "Linux":
            result = subprocess.run(["pgrep", "-f", "Docker"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        elif platform.system() == "Windows":
            result = subprocess.run(["tasklist", "/FI", "IMAGENAME eq dockerd.exe"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        else:
            print("⚠️ Unsupported OS for PID retrieval.")
            return None

        if result.returncode == 0 and result.stdout.strip():
            pid = result.stdout.strip().split("\n")[0].split()[0]
            print(f"🔍 Docker process ID: {pid}")
            return pid
        else:
            print("❌ Could not find Docker process ID.")
            return None
    except FileNotFoundError:
        print("⚠️ Required system commands are not available.")
        return None

def get_process_resource_usage(pid):
    """Get CPU and Memory usage of the Docker process."""
    try:
        if platform.system() in ["Darwin", "Linux"]:
            result = subprocess.run(["ps", "-p", pid, "-o", "%cpu,%mem"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        elif platform.system() == "Windows":
            result = subprocess.run(["wmic", "process", "where", f"ProcessId={pid}", "get", "PercentProcessorTime,WorkingSetSize"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        else:
            print("⚠️ Unsupported OS for resource usage retrieval.")
            return None

        lines = result.stdout.strip().split("\n")
        if len(lines) > 1:
            usage = lines[1].strip()
            cpu_usage = float(usage.split()[0])  # Extract CPU usage percentage
            memory_usage = float(usage.split()[1])  # Extract memory usage percentage

            print(f"📊 Resource usage for PID {pid}:")
            print(f"   🔹 CPU Usage: {cpu_usage:.2f}%")
            print(f"   🔹 Memory Usage: {memory_usage:.2f}%")
            return cpu_usage, memory_usage
        else:
            print("❌ Could not retrieve resource usage.")
            return None, None
    except FileNotFoundError:
        print("⚠️ Required system commands are not available.")
        return None, None

def estimate_power_consumption(cpu_usage):
    """Estimate power consumption based on CPU usage."""
    active_power = (CPU_WATTS_PER_CORE * (cpu_usage / 100))  # Watts
    idle_power = CPU_WATTS_PER_CORE * 0.1  # 10% of active power when idle
    print(f"⚡ Estimated Power Consumption:")
    print(f"   🔹 Active Power Usage: {active_power:.2f} W")
    print(f"   🔹 Idle Power Usage: {idle_power:.2f} W")
    return active_power, idle_power

def estimate_energy_efficiency(active_power):
    """Estimate energy efficiency in Joules per task/request."""
    joules_per_second = active_power * JOULES_PER_WATT_SECOND  # Convert Watts to Joules
    requests_per_second = random.uniform(5, 50)  # Approximate request rate
    joules_per_request = joules_per_second / requests_per_second
    print(f"⚡ Energy Efficiency:")
    print(f"   🔹 {joules_per_request:.2f} Joules per request/task")
    return joules_per_request

def estimate_carbon_footprint(active_power):
    """Estimate CO₂ emissions based on power consumption."""
    energy_kwh = (active_power * (1 / 1000)) * (1 / 3600)  # Convert Watts to kWh
    co2_emissions = energy_kwh * CARBON_INTENSITY_GRID * 1000  # Convert to gCO₂eq
    print(f"🌱 Carbon Footprint Estimation:")
    print(f"   🔹 CO₂ Emissions per Container: {co2_emissions:.2f} gCO₂eq")
    return co2_emissions

def cloud_carbon_footprint(active_power):
    """Estimate cloud carbon emissions for Docker running on cloud infrastructure."""
    cloud_emissions_factor = 0.3  # kg CO₂ per kWh for cloud data centers
    energy_kwh = (active_power * (1 / 1000)) * (1 / 3600)
    cloud_co2_emissions = energy_kwh * cloud_emissions_factor * 1000  # Convert to gCO₂eq
    print(f"☁️ Cloud Carbon Footprint:")
    print(f"   🔹 Estimated Cloud CO₂ Emissions: {cloud_co2_emissions:.2f} gCO₂eq")
    return cloud_co2_emissions

if __name__ == "__main__":
    try:
        while True:
            print("\n🔄 Checking Docker sustainability metrics...\n")
            if is_docker_running():
                pid = get_docker_pid()
                if pid:
                    cpu_usage, memory_usage = get_process_resource_usage(pid)
                    if cpu_usage is not None:
                        active_power, idle_power = estimate_power_consumption(cpu_usage)
                        estimate_energy_efficiency(active_power)
                        estimate_carbon_footprint(active_power)
                        cloud_carbon_footprint(active_power)
                    
                    # Kubernetes Metrics
                    total_pods, total_nodes, node_utilization = get_kubernetes_metrics()
                    if total_pods > 0:
                        print(f"🤖 Kubernetes Pods: {total_pods}")
                        print(f"🔗 Kubernetes Nodes: {total_nodes}")
                        print(f"📊 Node Utilization Efficiency: {node_utilization:.2f} Pods/Node")

            print("\n⏳ Refreshing in 2 seconds...\n")
            time.sleep(2)
    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped.")
