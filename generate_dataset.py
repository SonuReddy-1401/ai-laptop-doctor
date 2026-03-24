import json
import random
import os

# Define the paths for the output JSONL dataset
OUTPUT_FILE = "fine_tuning_dataset.jsonl"
NUM_EXAMPLES = 500

# Base templates for generating synthetic laptop telemetry
def generate_base_telemetry():
    return {
        "timestamp": "2026-03-18 10:00:00",
        "system": {
            "cpu_model": random.choice(["Intel Core i5-13450HX", "AMD Ryzen 7 5800H", "Intel Core i7-12700H", "AMD Ryzen 9 7945HX"]),
            "cpu_usage_pct": round(random.uniform(5.0, 95.0), 1),
            "ram_usage_pct": round(random.uniform(30.0, 95.0), 1),
            "ram_available_gb": round(random.uniform(1.0, 16.0), 2),
            "system_uptime": f"{round(random.uniform(1.0, 100.0), 2)} hours"
        },
        "top_5_apps": [
            {"name": "chrome.exe", "ram_pct": round(random.uniform(1.0, 15.0), 1)},
            {"name": "Discord.exe", "ram_pct": round(random.uniform(0.5, 5.0), 1)},
            {"name": "Code.exe", "ram_pct": round(random.uniform(1.0, 10.0), 1)},
            {"name": "explorer.exe", "ram_pct": round(random.uniform(0.5, 3.0), 1)},
            {"name": "Spotify.exe", "ram_pct": round(random.uniform(0.5, 2.0), 1)}
        ],
        "thermals": {
            "temp_c": round(random.uniform(40.0, 95.0), 1),
            "fan_rpm": random.choice(["Hardware Locked (OEM Managed)", "3500 RPM", "5500 RPM", "Active State"])
        },
        "battery_health": {
            "current_pct": random.randint(10, 100),
            "is_plugged": random.choice([True, False]),
            "design_capacity": 60000,
            "full_charge_capacity": random.randint(40000, 60000),
            "wear_level_pct": round(random.uniform(0.0, 30.0), 2)
        },
        "disk_performance": {
            "ssd_smart_status": random.choice(["Healthy (WMI Verified)", "WARNING: Failure Predicted"]),
            "free_gb": round(random.uniform(5.0, 500.0), 2),
            "usage_pct": round(random.uniform(10.0, 99.0), 1),
            "read_latency_ms": round(random.uniform(0.0, 10.0), 2),
            "write_latency_ms": round(random.uniform(0.0, 10.0), 2)
        },
        "faulty_drivers": "All Drivers OK",
        "recent_logs": []
    }

# Synthetic Scenarios defining how the data and question map to an action
SCENARIOS = [
    {
        "category": "High RAM",
        "user_queries": ["my laptop is running slow", "why is it lagging", "everything is stuttering", "laptop is freezing"],
        "action": "optimize_ram",
        "trigger": lambda t: t["system"].update({"ram_usage_pct": round(random.uniform(85.0, 99.0), 1)}),
        "diagnosis": "Telemetry indicates very high RAM usage, which is likely causing the stuttering and interface lag you are experiencing.",
        "reasoning": "Running optimize_ram will restart Windows Explorer and clear the DNS cache, freeing up resources and reducing UI lag."
    },
    {
        "category": "Disk Full",
        "user_queries": ["im out of space", "drive is full", "cant install new game", "disk cleanup needed", "storage is full"],
        "action": "cleanup_system_junk",
        "trigger": lambda t: t["disk_performance"].update({"usage_pct": round(random.uniform(90.0, 99.0), 1), "free_gb": round(random.uniform(1.0, 10.0), 2)}),
        "diagnosis": "The system disk is nearly full, exceeding 90% usage, which prevents local file storage and can throttle overall system speed.",
        "reasoning": "Executing cleanup_system_junk will permanently delete Windows Temp and Prefetch files, reclaiming critical space."
    },
    {
        "category": "Driver Issues",
        "user_queries": ["usb driving not working", "camera glitched", "wifi keeps dropping", "bluetooth is dead"],
        "action": "rescan_drivers",
        "trigger": lambda t: t.update({"faulty_drivers": [{"name": "Intel(R) Wireless-AC", "error_code": 43, "status": "Error"}]}),
        "diagnosis": "The Device Manager has flagged an error (Code 43) with one or more hardware drivers.",
        "reasoning": "Forcing Windows to rescan Plug-and-Play devices can resolve isolated driver hangs and reinitialize hardware components."
    },
    {
        "category": "Battery Report",
        "user_queries": ["battery life is bad", "battery dying fast", "check battery health", "how is my battery doing"],
        "action": "generate_battery_health_html",
        "trigger": lambda t: t["battery_health"].update({"wear_level_pct": round(random.uniform(5.0, 30.0), 2)}),
        "diagnosis": "Your battery shows signs of degradation.",
        "reasoning": "Generating a detailed battery report will provide granular historical data on charge cycles and physical cell wear."
    },
    {
        "category": "Hardware (No Action)",
        "user_queries": ["my screen is cracked", "keycap fell off", "laptop fell in pool", "fan is making grinding noise"],
        "action": None,
        "trigger": lambda t: None, # Normal telemetry
        "diagnosis": "The issue described is physical hardware damage, which cannot be diagnosed or solved via software telemetry.",
        "reasoning": "No automated software action can repair physical damage. Please consult a professional hardware repair technician."
    },
    {
        "category": "Normal Queries (No Action)",
        "user_queries": ["how do I use word", "open browser", "what is my cpu", "check for my driver updates"],
        "action": None,
        "trigger": lambda t: None, # Normal telemetry ensures no triggers fire
        "diagnosis": "The telemetry data shows the system is running optimally with no errors flagged.",
        "reasoning": "Because there are no anomalies in the hardware sensors, no automated diagnostic action is required at this time."
    }
]

def generate_entry():
    # Pick a random scenario
    scenario = random.choice(SCENARIOS)
    
    # Generate base telemetry
    telemetry = generate_base_telemetry()
    
    # Apply the trigger to mutate the telemetry so it matches the scenario
    scenario["trigger"](telemetry)
    
    # Pick a random query mapped to this scenario
    user_query = random.choice(scenario["user_queries"])
    
    # Structure the expected LLM output
    expected_response = {
        "diagnosis": scenario["diagnosis"],
        "proposed_action": scenario["action"],
        "reasoning": scenario["reasoning"]
    }
    
    # Structure the message format typical for Chat-based fine-tuning (e.g. OpenAI format or Llama/Qwen prompt formatting)
    # We will output a generic system/user/assistant message array.
    entry = {
        "messages": [
            {
                "role": "system",
                "content": "You are an Expert Laptop Repair AI. You must analyze the User Question alongside the Telemetry JSON. If you are not 100% certain an action will resolve the issue, you MUST return null for proposed_action. Respond ONLY in structured JSON."
            },
            {
                "role": "user",
                "content": f"USER QUESTION: {user_query}\n\nCURRENT LAPTOP TELEMETRY:\n{json.dumps(telemetry, indent=2)}"
            },
            {
                "role": "assistant",
                "content": json.dumps(expected_response, indent=2)
            }
        ]
    }
    return entry

def main():
    print(f"Generating {NUM_EXAMPLES} synthetic examples...")
    dataset = []
    
    for _ in range(NUM_EXAMPLES):
        dataset.append(generate_entry())
        
    print(f"Writing to {OUTPUT_FILE} in JSONL format...")
    with open(OUTPUT_FILE, 'w') as f:
        for entry in dataset:
            f.write(json.dumps(entry) + '\n')
            
    print("Done! You can now use this dataset to fine-tune an LLM.")

if __name__ == "__main__":
    main()
