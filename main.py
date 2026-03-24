import json
import os
import sys
import argparse
import subprocess
from langchain_ollama import OllamaLLM
from knowledge_base import LaptopKnowledgeBase
from actions import LaptopActions

class LaptopDoctorAgent:
    def __init__(self, model="qwen3.5:latest"):
        # Initialize the AI Brain with the selected model
        self.llm = OllamaLLM(model=model)
        # Initialize the Knowledge Base 
        # We hardcode the embeddings to 'llama3.2' since the ChromaDB was built using it!
        self.kb = LaptopKnowledgeBase()

    def get_scan_data(self):
        """Runs sensors.py to generate fresh telemetry, then reads it."""
        try:
            print("[System] Scanning hardware and pulling fresh logs...")
            # Run sensors.py silently using sys.executable to maintain the virtual environment
            subprocess.run([sys.executable, "sensors.py"], capture_output=True, check=True)
        except Exception as e:
            print(f"[!] Warning: Could not run sensors.py automatically: {e}")
            
        if not os.path.exists("last_scan.json"):
            print("[!] Error: last_scan.json not found even after running sensors.py.")
            return None
            
        with open("last_scan.json", "r") as f:
            return json.load(f)

    def get_action_descriptions(self):
        return json.dumps(LaptopActions.ACTION_REGISTRY, indent=2)

    def ask_for_permission(self, proposed_action, diagnosis, reasoning, secondary_issues=None):
        """Asks the user for permission to execute the proposed action."""
        if not proposed_action or proposed_action not in LaptopActions.ACTION_REGISTRY:
            print(f"\n[Doctor's Diagnosis] {diagnosis}")
            if secondary_issues and str(secondary_issues).lower() not in ["null", "none", ""]:
                print(f"[Secondary Issues] {secondary_issues}")
            print(f"[Reasoning] {reasoning}")
            print("\n[AI] No automated action is required or possible for this issue.")
            return False

        print(f"\n" + "="*50)
        print(f"🩺  DOCTOR'S DIAGNOSIS")
        print(f"="*50)
        print(f"DIAGNOSIS: {diagnosis}")
        if secondary_issues and str(secondary_issues).lower() not in ["null", "none", ""]:
            print(f"\n⚠️ SECONDARY OBSERVATIONS: {secondary_issues}")
        print(f"\nREASONING: {reasoning}")
        print(f"\n[PROPOSED ACTION]: {proposed_action}")
        print(f"Description: {LaptopActions.ACTION_REGISTRY.get(proposed_action)}")
        
        while True:
            choice = input(f"\n[?] Do you allow me to execute '{proposed_action}'? [ok/no]: ").strip().lower()
            if choice == 'ok':
                return True
            elif choice == 'no':
                print("[!] Action cancelled by user.")
                return False
            else:
                print("Invalid input. Please type 'ok' or 'no'.")

    def execute_action(self, action_name):
        """Dynamically executes the function from LaptopActions if it exists."""
        if action_name and hasattr(LaptopActions, action_name):
            method = getattr(LaptopActions, action_name)
            result = method()
            print(f"\n[Action Result] {result}")
        else:
            print("\n[!] Error: Invalid action requested.")

    def run_doctor(self, user_query):
        data = self.get_scan_data()
        if not data: return

        print(f"\n[Doctor] Analyzing query and system telemetry...")
        
        # Search the 5 PDFs for the specific answer
        context_chunks = self.kb.query(user_query)
        context_text = "\n".join(context_chunks)

        # Formulate the response using LLM + Manual Context + Sensor Data
        prompt = f"""
        You are an Expert Laptop Repair AI.
        
        USER QUESTION: {user_query}
        
        CURRENT LAPTOP TELEMETRY:
        {json.dumps(data, indent=2)}
        
        TECHNICAL MANUAL CONTEXT (HP/LENOVO):
        {context_text}
        
        AVAILABLE AUTOMATED ACTIONS:
        {self.get_action_descriptions()}
        
        CRITICAL INSTRUCTIONS & NEGATIVE CONSTRAINTS:
        1. Analyze the user's question, the telemetry, and the manual context.
        2. Decide if one of the EXACT AVAILABLE AUTOMATED ACTIONS should be run to help fix the issue.
        3. TRANSPARENCY: Always explain complex technical terms (like NDIS, DPC Latency, S.M.A.R.T., etc.) in plain English so the user understands the root cause. (e.g. "NDIS is a Network Driver that crashed").
        4. OVERRIDE PRIORITIES:
           - If the user complains of "slow", "lag", or "sluggish", propose 'optimize_ram' as the primary action. You MUST extract any background driver errors (like NDIS) and put them in `secondary_issues`. Never ignore driver errors.
           - If the user explicitly asks for a battery report, propose 'generate_battery_health_html' regardless of telemetry health.
           - If the user complains of a specific frozen/crashed app, propose 'kill_frozen_apps'.
        5. YOU MUST NEVER GUESS OR HALLUCINATE ACTIONS. If an action is not in the AVAILABLE AUTOMATED ACTIONS list, you cannot use it.
        6. If the telemetry data appears entirely normal, or if you are not 100% certain an action will resolve the issue, you MUST return null for `proposed_action`.
        7. If the user asks a question that requires a physical repair (e.g., cracked screen, broken keyboard), you MUST return null for `proposed_action`.
        
        FORMAT:
        Respond ONLY with a valid JSON object matching this exact schema:
        {{
            "diagnosis": "A plain-English explanation of the PRIMARY problem. Do NOT put secondary warnings from the event logs here.",
            "proposed_action": "The exact string key of the primary action to run (e.g. 'optimize_ram') OR null if no action is needed.",
            "reasoning": "Why you proposed this primary action or why no action is needed.",
            "secondary_issues": "MANDATORY IF LOGS SHOW ERRORS: If you see ANY warnings/errors in recent_logs (like NDIS, DCOM, etc.), extract them here! Define the acronyms and explain what they mean in plain English. If logs are perfectly clean and there is absolutely nothing else wrong, return 'null'."
        }}
        
        EXAMPLE VALID RESPONSE:
        {{
            "diagnosis": "The system RAM usage is perfectly healthy, but the user is experiencing intermittent visual stuttering.",
            "proposed_action": "optimize_ram",
            "reasoning": "Since the user complained of sluggishness, restarting Explorer and flushing DNS is the best immediate fix.",
            "secondary_issues": "The background event logs show multiple 'NDIS' warnings. NDIS stands for Network Driver Interface Specification. This means your Wi-Fi or Internet driver is briefly crashing and recovering, which is the true root cause of your laptop freezing."
        }}
        
        Do not include any extra text, markdown formatting like ```json, or explanations outside the JSON block.
        """
        
        # Generate AI Response
        response_text = self.llm.invoke(prompt)
        
        # Try to parse the JSON response
        try:
            # Clean up potential markdown formatting from the LLM
            clean_text = response_text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.startswith("```"):
                clean_text = clean_text[3:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
                
            response_json = json.loads(clean_text)
            diagnosis = response_json.get("diagnosis", "No diagnosis provided.")
            proposed_action = response_json.get("proposed_action")
            reasoning = response_json.get("reasoning", "No reasoning provided.")
            secondary_issues = response_json.get("secondary_issues")
            
            # Interactive Permission Flow
            if self.ask_for_permission(proposed_action, diagnosis, reasoning, secondary_issues):
                self.execute_action(proposed_action)
                
        except json.JSONDecodeError:
            print("\n[!] Error parsing AI response. The LLM did not return proper JSON.")
            print("Raw Response:", response_text)

def main_loop():
    parser = argparse.ArgumentParser(description="AI Laptop Doctor (Human-in-the-Loop CLI)")
    parser.add_argument("--model", type=str, default="qwen2.5:latest", help="The Ollama model to use (default: qwen2.5:latest)")
    args = parser.parse_args()

    # Ensure Ollama is running and the specified model is pulled!
    doc = LaptopDoctorAgent(model=args.model)
    
    print("="*60)
    print(f"WELCOME TO THE AI LAPTOP DOCTOR (Using Model: {args.model})")
    print("="*60)
    
    while True:
        try:
            user_input = input("\n[USER] Describe your laptop issue (or type 'exit' to quit): ").strip()
            if user_input.lower() in ['exit', 'quit']:
                print("Goodbye!")
                break
            if not user_input:
                continue
                
            doc.run_doctor(user_input)
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break

if __name__ == "__main__":
    main_loop()