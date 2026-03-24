import os
import subprocess
import shutil
import ctypes

class LaptopActions:
    ACTION_REGISTRY = {
        "optimize_ram": "Restarts Windows Explorer and flushes DNS to help with UI lag. Use when RAM is high or system is sluggish.",
        "cleanup_system_junk": "Cleans User and System Temp folders to free up disk space. Use when disk is full or user requests basic cleanup.",
        "rescan_drivers": "Forces Windows to rescan for hardware changes (fixes minor driver hangs). Use when USB devices or drivers act up.",
        "generate_battery_health_html": "Generates a detailed HTML battery report. Use when user asks about battery health or performance drops off charger.",
        "run_sfc_scan": "Triggers a System File Checker scan. Use for deep Windows corruption or severe unexplained crashes (takes 15-30 mins).",
        "reset_network_stack": "Flushes the network cache and releases/renews IP. Use when the user specifically complains about Wi-Fi disconnecting or missing internet.",
        "reset_print_spooler": "Clears the printing queue and restarts the print spooler. Use when the user says their printer is stuck or won't print.",
        "optimize_drives": "Runs Defrag/TRIM on the main system drive. Use for disk fragmentation or if the SSD is running slowly.",
        "kill_frozen_apps": "Force-kills any applications with a 'Not Responding' status. Use when an app is specifically mentioned as frozen or crashed.",
        "search_web_for_solution": "Searches the live internet for obscure error codes, Blue Screen codes, or unknown issues. Use when the manual and telemetry do not provide an obvious fix."
    }

    @staticmethod
    def optimize_ram():
        """Restarts Windows Explorer and flushes DNS to help with UI lag."""
        try:
            print("[Action] Optimizing RAM and UI...")
            os.system('taskkill /f /im explorer.exe & start explorer.exe')
            os.system('ipconfig /flushdns')
            return "Windows Explorer restarted and network cache flushed."
        except Exception as e:
            return f"Failed to optimize RAM: {e}"

    @staticmethod
    def cleanup_system_junk():
        """Cleans User and System Temp folders to free up disk space."""
        print("[Action] Cleaning system junk files...")
        paths_to_clean = [
            os.environ.get('TEMP'),
            r'C:\Windows\Temp',
            r'C:\Windows\Prefetch'
        ]
        count = 0
        deleted_log = []
        
        for path in paths_to_clean:
            if path and os.path.exists(path):
                try:
                    for filename in os.listdir(path):
                        file_path = os.path.join(path, filename)
                        try:
                            if os.path.isfile(file_path) or os.path.islink(file_path):
                                os.unlink(file_path)
                                deleted_log.append(file_path)
                                count += 1
                            elif os.path.isdir(file_path):
                                shutil.rmtree(file_path)
                                deleted_log.append(file_path)
                                count += 1
                        except Exception:
                            continue
                except PermissionError:
                    print(f"[Warning] Permission denied to access {path}. Skipping...")
                    continue
                    
        # Automatically generate and open the log file
        if count > 0:
            log_path = os.path.join(os.getcwd(), "deleted_junk_log.txt")
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(f"--- JUNK CLEANUP LOG ({count} items deleted) ---\n\n")
                f.write("\n".join(deleted_log))
            if hasattr(os, 'startfile'):
                os.startfile(log_path)
                
        return f"Cleanup complete. Removed {count} items/folders. (Log opened in editor)"

    @staticmethod
    def rescan_drivers():
        """Forces Windows to rescan for hardware changes and re-enable crashed drivers."""
        try:
            print("[Action] Attempting to repair and enable device drivers...")
            import subprocess
            
            # 1. Standard hardware rescan for new/missing devices
            subprocess.run(["pnputil", "/scan-devices"], capture_output=True)
            
            # 2. Advanced PowerShell command to find any disabled (Error 22)/Unknown devices and force them ON
            ps_script = "Get-PnpDevice | Where-Object { $_.Status -eq 'Error' -or $_.Status -eq 'Unknown' } | Enable-PnpDevice -Confirm:$false"
            
            process = subprocess.run(["powershell", "-Command", ps_script], capture_output=True, text=True)
            
            if "Access is denied" in process.stderr or "PermissionDenied" in process.stderr:
                return "Hardware rescan complete. [!] WARNING: You must run your terminal as Administrator to re-enable disabled devices!"
                
            return "Hardware rescan and repair complete. Disabled devices (like Bluetooth) were re-enabled."
        except Exception as e:
            return f"Failed to execute advanced driver repair: {e}"

    @staticmethod
    def generate_battery_health_html():
        """Generates a professional Windows Battery Report."""
        try:
            print("[Action] Generating detailed HTML battery report...")
            report_path = os.path.join(os.getcwd(), "battery_report.html")
            subprocess.run(['powercfg', '/batteryreport', '/output', report_path], check=True)
            
            # Automatically open the report in the default web browser (Windows only)
            if hasattr(os, 'startfile'):
                os.startfile(report_path)
                
            return f"Success! Report generated and opened in your browser."
        except Exception as e:
            return f"Failed to generate report: {e}"

    @staticmethod
    def run_sfc_scan():
        """Triggers a System File Checker scan (Needs Admin)."""
        print("[Action] Initiating System File Checker...")
        # Note: This is a long process, we run it as a detached process
        try:
            subprocess.Popen(['sfc', '/scannow'], shell=True)
            return "SFC Scan initiated in a new window. This may take 15-30 minutes."
        except Exception as e:
            return f"Could not start SFC: {e}"

    @staticmethod
    def reset_network_stack():
        """Resets the Winsock and IP stack to fix internet issues."""
        try:
            print("[Action] Resetting network stack and renewing IP...")
            subprocess.run(['netsh', 'winsock', 'reset'], capture_output=True, check=True)
            os.system('ipconfig /release & ipconfig /renew')
            return "Network stack reset successfully. A PC restart may be required for full effect."
        except subprocess.CalledProcessError as e:
            if e.returncode == 5:
                return "Permission Denied: Administrator rights are required to reset Winsock."
            return f"Network stack reset failed: code {e.returncode}"
        except Exception as e:
            return f"Failed to reset network stack: {e}"

    @staticmethod
    def reset_print_spooler():
        """Clears stuck print jobs and restarts the spooler service."""
        try:
            print("[Action] Resetting Print Spooler and clearing stuck print jobs...")
            subprocess.run(['net', 'stop', 'spooler'], capture_output=True, check=True)
            
            # Clear the PRINTERS folder
            spool_dir = r"C:\Windows\System32\spool\PRINTERS"
            if os.path.exists(spool_dir):
                for filename in os.listdir(spool_dir):
                    file_path = os.path.join(spool_dir, filename)
                    try:
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                    except Exception:
                        pass
                        
            subprocess.run(['net', 'start', 'spooler'], capture_output=True, check=True)
            return "Print Spooler restarted and stuck print jobs successfully cleared."
        except subprocess.CalledProcessError as e:
            if e.returncode == 5:
                return "Permission Denied: Administrator rights are required to restart Windows services."
            return f"Service restart failed: code {e.returncode}"
        except Exception as e:
            return f"Failed to reset print spooler: {e}"

    @staticmethod
    def optimize_drives():
        """Runs the Windows built-in drive optimizer (Defrag/TRIM)."""
        try:
            print("[Action] Optimizing system drive (Defrag/TRIM) - This may take a moment...")
            subprocess.run(['defrag', 'C:', '/O'], capture_output=True, check=True)
            return "Drive C: successfully optimized/trimmed."
        except subprocess.CalledProcessError as e:
            if e.returncode == 5:
                return "Permission Denied: Administrator rights are required to optimize drives."
            return f"Drive optimization failed: code {e.returncode}"
        except Exception as e:
            return f"Failed to optimize drives: {e}"

    @staticmethod
    def kill_frozen_apps():
        """Kills any application with a 'Not Responding' status or a specific app chosen by the user."""
        try:
            print("[Action] Searching for generically 'Not Responding' applications...")
            result = subprocess.run(['taskkill', '/F', '/FI', 'STATUS eq NOT RESPONDING'], capture_output=True, text=True)
            
            output_msg = ""
            if "INFO:" in result.stdout and "No tasks" in result.stdout:
                output_msg += "No universally 'frozen' applications flagged by Windows.\n"
            else:
                output_msg += "Successfully terminated system-flagged frozen applications.\n"
                
            print("\n" + output_msg.strip())
            
            # Allow the user to manually target an unflagged but frozen app
            target = input("\n[?] Is there a SPECIFIC app you still want to force close? (Type name or press Enter to skip): ").strip()
            
            if target:
                target_base = target.lower()
                if target_base.endswith(".exe"):
                    target_base = target_base[:-4]
                    
                # Map colloquial names to actual Windows .exe names
                common_aliases = {
                    "word": "winword",
                    "powerpoint": "powerpnt",
                    "excel": "excel",
                    "outlook": "outlook",
                    "chrome": "chrome",
                    "edge": "msedge",
                    "notepad": "notepad",
                    "vscode": "code",
                    "discord": "discord",
                    "spotify": "spotify",
                    "teams": "ms-teams",
                    "whatsapp": "whatsapp",
                    "file explorer": "explorer",
                    "explorer": "explorer"
                }
                
                # Retrieve the mapped executable if it exists, otherwise keep user input
                mapped_target = common_aliases.get(target_base, target_base)
                final_target = mapped_target + ".exe"
                    
                # 1. Check if the app is running at all
                check_run = subprocess.run(['tasklist', '/FI', f'IMAGENAME eq {final_target}', '/NH'], capture_output=True, text=True)
                if "INFO: No tasks" in check_run.stdout:
                    output_msg += f"\nSkipped: {final_target} is not currently running."
                    return output_msg.strip()
                    
                # 2. Check if the app is explicitly flagged as 'Not Responding'
                check_frozen = subprocess.run(['tasklist', '/FI', f'IMAGENAME eq {final_target}', '/FI', 'STATUS eq NOT RESPONDING', '/NH'], capture_output=True, text=True)
                is_flagged_frozen = "INFO: No tasks" not in check_frozen.stdout
                
                # 3. Decision Logic
                proceed_with_kill = False
                if is_flagged_frozen:
                    print(f"\n[Action] Confirmed: {final_target} is frozen. Force killing...")
                    proceed_with_kill = True
                else:
                    print(f"\n[⚠️ WARNING] Windows reports that '{final_target}' is HEALTHY and responding normally.")
                    confirm = input(f"[?] Force-closing it will destroy any unsaved work! Are you absolutely sure? [y/n]: ").strip().lower()
                    if confirm == 'y':
                        print(f"\n[Action] Force killing healthy app {final_target}...")
                        proceed_with_kill = True
                    else:
                        output_msg += f"\nSafety Abort: User cancelled force-close of healthy app {final_target}."
                
                # 4. Execute Kill if approved
                if proceed_with_kill:
                    kill_result = subprocess.run(['taskkill', '/F', '/IM', final_target, '/T'], capture_output=True, text=True)
                    if kill_result.returncode == 0:
                        output_msg += f"\nSuccessfully force-closed {final_target}."
                    elif kill_result.returncode == 5:
                        output_msg += f"\nPermission Denied: Administrator rights are required to kill {final_target}."
                    else:
                        output_msg += f"\nFailed to close {final_target}. (Exit Code: {kill_result.returncode})"
            
            return output_msg.strip()
            
        except Exception as e:
            return f"Failed to kill apps: {e}"

    @staticmethod
    def search_web_for_solution():
        """Searches DuckDuckGo for obscure Windows error codes or BSODs."""
        try:
            print("[Action] Let's check the internet for a solution.")
            query = input("\n[?] Enter the specific error code or issue to search for: ").strip()
            if not query:
                return "Web search cancelled (no query provided)."
                
            print(f"[Action] Searching DuckDuckGo for: '{query}'...")
            from ddgs import DDGS
            
            # Fetch top 3 results
            results = DDGS().text(query, max_results=3)
            
            if not results:
                return f"No results found for '{query}'."
                
            formatted_results = "\n\n--- TOP 3 WEB RESULTS ---\n"
            for i, res in enumerate(results, 1):
                formatted_results += f"{i}. {res.get('title')}\n   {res.get('body')}\n   Source: {res.get('href')}\n\n"
                
            return formatted_results.strip()
            
        except ImportError:
            return "Failed: ddgs package is missing. Run 'pip install ddgs'."
        except Exception as e:
            return f"Web search failed: {e}"

if __name__ == "__main__":
    print("Testing Laptop Actions Toolkit...")
    # Example: Run a quick cleanup
    print(LaptopActions.cleanup_system_junk())