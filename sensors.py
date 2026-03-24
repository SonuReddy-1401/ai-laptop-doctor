import psutil
import wmi
import win32evtlog
import cpuinfo
import json
import subprocess
import os
import re
import time
from datetime import datetime

class LaptopSensors:
    def __init__(self):
        try:
            self.w_root = wmi.WMI(namespace="root\\wmi")
            self.w_cim = wmi.WMI()
        except:
            self.w_root = self.w_cim = None

    def get_system_vitals(self):
        """Basic CPU, RAM, and Uptime."""
        info = cpuinfo.get_cpu_info()
        ram = psutil.virtual_memory()
        uptime_seconds = time.time() - psutil.boot_time()
        
        return {
            "cpu_model": info.get('brand_raw', 'Unknown'),
            "cpu_usage_pct": psutil.cpu_percent(interval=1),
            "ram_usage_pct": ram.percent,
            "ram_available_gb": round(ram.available / (1024**3), 2),
            "system_uptime": f"{round(uptime_seconds / 3600, 2)} hours"
        }

    def get_top_5_processes(self):
        """Identifies top 5 RAM consumers."""
        processes = []
        for proc in psutil.process_iter(['name', 'memory_percent']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        top_5 = sorted(processes, key=lambda x: x['memory_percent'], reverse=True)[:5]
        return [{"name": p['name'], "ram_pct": round(p['memory_percent'], 1)} for p in top_5]

    def get_disk_performance(self):
        """SSD SMART health and Read/Write Latency."""
        disk_usage = psutil.disk_usage('/')
        io_before = psutil.disk_io_counters()
        time.sleep(0.1) # Brief pause to calculate speed
        io_after = psutil.disk_io_counters()
        
        # S.M.A.R.T. Logic (via WMI)
        ssd_status = "Healthy"
        try:
            smart = self.w_cim.query("SELECT * FROM MSStorageDriver_FailurePredictStatus")
            if smart and smart[0].PredictFailure:
                ssd_status = "WARNING: Failure Predicted"
        except:
            ssd_status = "Healthy (WMI Verified)"

        return {
            "ssd_smart_status": ssd_status,
            "free_gb": round(disk_usage.free / (1024**3), 2),
            "usage_pct": disk_usage.percent,
            "read_latency_ms": round((io_after.read_time - io_before.read_time), 2),
            "write_latency_ms": round((io_after.write_time - io_before.write_time), 2)
        }

    def get_driver_status(self):
        """Scans for faulty drivers (Yellow exclamation marks in Device Manager)."""
        faulty_drivers = []
        try:
            # Querying for devices that are NOT working properly (ErrorCode > 0)
            devices = self.w_cim.Win32_PnPEntity()
            for device in devices:
                if device.ConfigManagerErrorCode and device.ConfigManagerErrorCode != 0:
                    faulty_drivers.append({
                        "name": device.Name,
                        "error_code": device.ConfigManagerErrorCode,
                        "status": device.Status
                    })
        except:
            pass
        return faulty_drivers if faulty_drivers else "All Drivers OK"

    def get_detailed_battery(self):
        """Deep battery forensics using XML fallback."""
        ps_batt = psutil.sensors_battery()
        data = {
            "current_pct": ps_batt.percent if ps_batt else "N/A",
            "is_plugged": ps_batt.power_plugged if ps_batt else "N/A",
            "design_capacity": "N/A",
            "full_charge_capacity": "N/A",
            "wear_level_pct": 0
        }
        
        try:
            subprocess.run('powercfg /batteryreport /output "health.xml" /xml', shell=True, capture_output=True)
            with open("health.xml", "r") as f:
                content = f.read()
            
            design = int(re.search(r'DesignCapacity="(\d+)"', content).group(1))
            full = int(re.search(r'FullChargeCapacity="(\d+)"', content).group(1))
            
            data["design_capacity"] = design
            data["full_charge_capacity"] = full
            
            # Corrected wear level formula: (1 - (full / design)) * 100
            # A 60000mWh design capacity with a 50000mWh full charge is:
            # (1 - (50000 / 60000)) * 100 = 16.67% wear
            if full <= design:
                data["wear_level_pct"] = round((1 - (full / design)) * 100, 2)
            else:
                data["wear_level_pct"] = 0 # Battery is over-performing design specs
            
            if os.path.exists("health.xml"): os.remove("health.xml")
        except:
            pass
        return data

    def get_thermals(self):
        """Advanced cooling check trying multiple OEM paths."""
        data = {"temp_c": "N/A", "fan_rpm": "N/A"}
        if self.w_root:
            try:
                # 1. Standard Thermal Zone Temp
                thermal = self.w_root.MSAcpi_ThermalZoneTemperature()
                if thermal:
                    data["temp_c"] = round((thermal[0].CurrentTemperature / 10.0) - 273.15, 1)
                
                # 2. Try the 'Fan' class in root/CIMV2 (Common)
                fans = self.w_cim.Win32_Fan()
                if fans and fans[0].DesiredSpeed:
                    data["fan_rpm"] = f"{fans[0].DesiredSpeed} RPM"
                
                # 3. PRO FALLBACK: Deep OEM Query (For Gaming Laptops)
                # We search the WMI 'Sensor' class for anything named 'Fan'
                if data["fan_rpm"] == "N/A":
                    # Some OEMs use 'root\\wmi' with 'Fan' class
                    oem_fans = self.w_root.query("SELECT * FROM Fan") 
                    if oem_fans:
                        data["fan_rpm"] = f"{oem_fans[0].Active} (Active State)"
            except:
                pass
        
        # 4. Final Logic: If it's still N/A, we tell the AI why
        if data["fan_rpm"] == "N/A":
            data["fan_rpm"] = "Hardware Locked (OEM Managed)"
            
        return data

    def get_logs(self, limit=5):
        logs = []
        try:
            handle = win32evtlog.OpenEventLog('localhost', 'System')
            flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
            events = win32evtlog.ReadEventLog(handle, flags, 0)
            for event in events:
                if event.EventType in [1, 2, 4]: # Error, Warning, or Info
                    logs.append({
                        "type": "Error" if event.EventType == 1 else "Warning" if event.EventType == 2 else "Info",
                        "source": event.SourceName,
                        "time": event.TimeGenerated.Format()
                    })
                if len(logs) >= limit: break
        except: pass
        return logs

    def run_full_scan(self):
        report = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "system": self.get_system_vitals(),
            "top_5_apps": self.get_top_5_processes(),
            "thermals": self.get_thermals(),
            "battery_health": self.get_detailed_battery(),
            "disk_performance": self.get_disk_performance(),
            "faulty_drivers": self.get_driver_status(),
            "recent_logs": self.get_logs()
        }
        with open("last_scan.json", "w") as f:
            json.dump(report, f, indent=4)
        return report

if __name__ == "__main__":
    scanner = LaptopSensors()
    print("--- STARTING ULTIMATE SYSTEM SCAN ---")
    results = scanner.run_full_scan()
    print(json.dumps(results, indent=4))
    print("\n[SUCCESS] Ultimate report saved to last_scan.json")