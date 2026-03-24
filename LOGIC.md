# AI Laptop Doctor — Core Logic & Architecture

This document serves as a deep-dive into the AI Laptop Doctor's diagnostic reasoning, specific action triggers, and multi-step workflows. Much of this logic is driven by the prompt engineering and the carefully constructed JSON execution loop within `main.py`.

---

## 1. General Maintenance & Optimization

The AI handles vague user complaints by executing non-destructive, high-impact routines to restore system responsiveness.

### `optimize_ram`
*   **Example User Trigger**: *"My computer is feeling very slow today."*
*   **Mechanism**: Restarts `explorer.exe` (Windows Explorer) and flushes the DNS cache (`ipconfig /flushdns`).
*   **Benefit**: This instantly frees up leaked RAM from the Windows desktop environment and cures UI stuttering without requiring a full system reboot.

### `cleanup_system_junk`
*   **Example User Trigger**: *"I think my drives feeling low, can you clean up my temp files?"*
*   **Mechanism**: Employs `os.unlink()` and `shutil.rmtree()` targeting `%TEMP%`, `C:\Windows\Temp`, and `C:\Windows\Prefetch`.
*   **Notes**: The AI will safely skip files that are currently locked by the OS. In tests, this routinely clears thousands of unnecessary files and folders.

---

## 2. Software Errors & The 3-Step "Freeze" Workflow

The AI uses a sophisticated flow for handling frozen or misbehaving applications. 

When a user complains about a frozen app (e.g., *"Discord is frozen"*), the logic follows three steps:

1.  **Step 1: The Native Kill**: 
    The system automatically identifies and terminates any applications officially flagged by the Windows OS as "Not Responding" using `taskkill /F /FI "STATUS eq NOT RESPONDING"`.
2.  **Step 2: Interactive Prompt**: 
    If the application is not naturally flagged by Windows, the AI asks the user for the specific application name. The system maps the natural language name (e.g., "word", "powerpoint") to the underlying executable (e.g., `winword.exe`, `powerpnt.exe`).
3.  **Step 3: The Tasklist Check & Warning Zone**:
    The system checks the status of the requested executable:
    *   **Scenario A**: If the app isn't actually running, it informs the user and aborts.
    *   **Scenario B**: If the app is confirmed to be "Not Responding," it is killed immediately.
    *   **Scenario C (Healthy App Warning)**: If the app is running normally but the user still wants to kill it, the AI issues a strict warning: *"⚠️ Windows reports that [app] is healthy. Force-closing it will result in the loss of unsaved data! Are you absolutely sure?"*

---

## 3. Hardware & Driver Diagnostic Logic

The AI fuses telemetry data with context to make intelligent hardware-level decisions.

### Intermittent Blue Screens or Crashing
*   **Logic**: If a user reports intermittent crashing, the AI cross-references real-time telemetry. For example, if RAM is at 85.3% and CPU is at 22%, the AI diagnoses potential overheating or driver instability.
*   **Action Taken**: Because this is a serious root-cause hardware issue, the AI correctly determines that **no automated fix applies**, preferring user caution over dangerous system guesses.

### Battery Fast Drain / Health
*   **Trigger**: *"Can you generate a battery report for me?"* or complaints of fast battery drain.
*   **Logic**: If the laptop is on AC power but dropping (e.g., stuck at 41%), the AI notes the paradox. Since telemetry shows no immediate "failure," it diagnoses intense background processes or general battery degradation, and proposes the generation of an HTML battery report rather than an automated fix.

### `rescan_drivers`
*   **Trigger**: Connectivity issues, e.g., *"My USB mouse isn't working."*
*   **Logic**: Forces Windows to run a Plug-and-Play rescan (`pnputil /scan-devices`) to attempt a re-mount of the unrecognized hardware.

---

## 4. Network Troubleshooting

*   **Trigger**: *"My Wi-Fi is connected but I don't have any internet access."*
*   **Action**: `reset_network_stack`
*   **Logic**: Network stack resets wipe outdated or corrupted DNS caches and renew the IP address. A clogged DNS cache can often emulate a completely disconnected state or severe network lag; this action fixes that at the root level without requiring router restarts.
