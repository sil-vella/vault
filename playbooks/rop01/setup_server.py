#!/usr/bin/env python3

import os
import sys
import subprocess
import logging
import time
from pathlib import Path
import shutil
import json

# Configure logging
log_dir = Path(__file__).parent / 'logs'
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f'setup_{time.strftime("%Y%m%d_%H%M%S")}.log'

# Get VM name from user
vm_name = input("Please enter the VM name: ").strip()
if not vm_name:
    print("Error: VM name cannot be empty")
    sys.exit(1)

# Get sudo password once at the beginning
sudo_password = input("Please enter your sudo password (will be used throughout the setup): ").strip()
if not sudo_password:
    print("Error: Sudo password cannot be empty")
    sys.exit(1)

# Menu for choosing starting point
menu_options = [
    "Start from the very beginning (all steps)",
    "Run: 01_configure_security.yml",
    "Run: 02_setup_k3s.yml",
    "Run: 05_setup_firewall.yml",
    "Run: 07_vault_initial_setup.yml",
    "Run: 08_store_vault_keys.yml",
    "Run: 09_verify_prerequisites.yml",
    "Run: 10_setup_unseal_scripts.yml",
    "Run: 11_configure_vault_auth.yml",
    "Run: 12_configure_flask_vault_access.yml"
]

print("\nWhere do you want to start the setup?")
for idx, option in enumerate(menu_options):
    print(f"  {idx+1}. {option}")
while True:
    try:
        start_choice = int(input("Enter the number of your choice: ")) - 1
        if 0 <= start_choice < len(menu_options):
            break
        else:
            print("Invalid choice. Try again.")
    except ValueError:
        print("Please enter a valid number.")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def get_sudo_password():
    """Get sudo password from user"""
    global sudo_password
    return sudo_password

def run_command(cmd, shell=False, interactive=False, env=None):
    """Run a command and log its output"""
    logger.info(f"Running command: {cmd}")
    try:
        if interactive:
            # For interactive commands, run without capture_output
            if env is None:
                env = os.environ.copy()
            
            if 'ansible-playbook' in cmd:
                process = subprocess.run(cmd.split() if not shell else cmd, shell=shell, check=True, env=env)
            else:
                process = subprocess.run(cmd.split() if not shell else cmd, shell=shell, check=True, env=env)
            return ""
        else:
            if shell:
                process = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True, timeout=180, env=env)
            else:
                process = subprocess.run(cmd.split(), check=True, capture_output=True, text=True, timeout=180, env=env)
            logger.info(f"Command output: {process.stdout}")
            return process.stdout.strip()
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out after 180 seconds: {cmd}")
        raise
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e.stderr}")
        raise

def run_playbook(playbook):
    logger.info(f"Running playbook: {playbook}")
    # Set environment variables for Ansible to use the stored password
    env = os.environ.copy()
    env['ANSIBLE_BECOME_PASSWORD'] = sudo_password
    
    # Run ansible-playbook with vm_name as extra variable
    run_command(f"ansible-playbook -i inventory.ini {playbook} -e vm_name={vm_name}", interactive=True, env=env)

def main():
    try:
        logger.info("Starting server setup process...")
        os.chdir(Path(__file__).parent)
        
        # Step index mapping - aligned with menu options
        steps = [
            ("playbook_01", lambda: run_playbook("01_configure_security.yml")),
            ("playbook_02", lambda: run_playbook("02_setup_k3s.yml")),
            ("playbook_05", lambda: run_playbook("05_setup_firewall.yml")),
            ("playbook_07", lambda: run_playbook("07_vault_initial_setup.yml")),
            ("playbook_08", lambda: run_playbook("08_store_vault_keys.yml")),
            ("playbook_09", lambda: run_playbook("09_verify_prerequisites.yml")),
            ("playbook_10", lambda: run_playbook("10_setup_unseal_scripts.yml")),
            ("playbook_11", lambda: run_playbook("11_configure_vault_auth.yml")),
            ("playbook_12", lambda: run_playbook("12_configure_flask_vault_access.yml")),
        ]
        
        # Map menu choice to step index
        # Menu option 0 = "Start from beginning" (run all steps)
        # Menu options 1-10 correspond to steps 0-9
        if start_choice == 0:
            # Start from the very beginning - run all steps
            run_range = range(len(steps))
        else:
            # Start from specific playbook
            run_range = range(start_choice - 1, len(steps))

        for i in run_range:
            step_name, step_func = steps[i]
            logger.info(f"Running step: {step_name}")
            step_func()
    except Exception as e:
        logger.error(f"Error during setup: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 