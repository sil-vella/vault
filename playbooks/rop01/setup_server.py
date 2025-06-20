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
    "Multipass authentication",
    "SSH key check/generation",
    "Multipass instance setup",
    "Update values.json",
    "Generate dynamic inventory",
    "Run: 00_ssh_for_new_user.yml",
    "Run: 01_configure_security.yml",
    "Run: 02_setup_k3s.yml",
    "Run: 03_setup_and_config_wg.yml",
    "WireGuard setup",
    "VPN connection test",
    "Run: 05_setup_firewall.yml",
    "Run: 06_harden_firewall.yml",
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

def restart_multipass_daemon():
    """Restart the Multipass daemon on macOS and try to recover from socket issues"""
    logger.info("Restarting Multipass daemon...")
    
    # First, try to stop all instances gracefully
    try:
        subprocess.run(["multipass", "stop", "--all"], check=False, timeout=30)
        logger.info("Stopped all Multipass instances")
    except Exception as e:
        logger.warning(f"Failed to stop instances gracefully: {e}")
    
    # Kill any remaining QEMU processes
    try:
        subprocess.run(["pkill", "-f", "qemu-system-x86_64"], check=False)
        time.sleep(3)
        logger.info("Killed remaining QEMU processes")
    except Exception as e:
        logger.warning(f"Failed to kill QEMU processes: {e}")
    
    # Restart the Multipass daemon
    try:
        subprocess.run([
            "sudo", "launchctl", "kickstart", "-k", "system/com.canonical.multipassd"
        ], check=True)
        logger.info("Multipass daemon restarted successfully.")
        # Add a longer delay to let the daemon fully restart
        time.sleep(10)
    except Exception as e:
        logger.error(f"Failed to restart Multipass daemon: {e}")
        # Try alternative restart method
        try:
            subprocess.run([
                "sudo", "launchctl", "unload", "/Library/LaunchDaemons/com.canonical.multipassd.plist"
            ], check=False)
            time.sleep(3)
            subprocess.run([
                "sudo", "launchctl", "load", "/Library/LaunchDaemons/com.canonical.multipassd.plist"
            ], check=False)
            time.sleep(10)
            logger.info("Used alternative method to restart Multipass daemon")
        except Exception as e2:
            logger.error(f"Alternative restart method also failed: {e2}")
    
    # Try to start instances again
    try:
        subprocess.run(["multipass", "start"], check=False, timeout=60)
        logger.info("Attempted to start all Multipass instances")
    except Exception as e:
        logger.warning(f"Failed to start instances: {e}")
    
    # Additional cleanup for the specific VM
    try:
        force_kill_vm(vm_name)
    except Exception as e:
        logger.warning(f"Failed to force kill specific VM: {e}")
    
    # Try to delete and purge the specific instance
    try:
        subprocess.run(f"multipass delete {vm_name} --purge", shell=True, check=False, timeout=30)
        logger.info(f"Deleted and purged instance {vm_name}")
    except Exception as e:
        logger.warning(f"Failed to delete/purge instance: {e}")
    
    # Final cleanup - remove any stale files
    try:
        multipass_data_dir = "/var/root/Library/Application Support/multipassd/qemu/vault/instances"
        if os.path.exists(f"{multipass_data_dir}/{vm_name}"):
            subprocess.run(["sudo", "rm", "-rf", f"{multipass_data_dir}/{vm_name}"], check=False)
            logger.info(f"Removed stale instance data for {vm_name}")
    except Exception as e:
        logger.warning(f"Failed to remove stale instance data: {e}")
    
    logger.info("Multipass daemon restart and cleanup complete.")

def check_multipass_auth():
    """Check and handle Multipass authentication, always recover and continue on error"""
    logger.info("Checking Multipass authentication...")
    try:
        subprocess.run(["multipass", "list"], check=True, capture_output=True, timeout=10)
        logger.info("Already authenticated with Multipass")
        return
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
        logger.warning(f"multipass list failed or timed out: {e}. Attempting to recover.")
        try:
            restart_multipass_daemon()
        except Exception as e2:
            logger.error(f"Failed to restart Multipass daemon: {e2}")
        # Always try to force kill and delete/purge the instance
        try:
            force_kill_vm(vm_name)
        except Exception as e3:
            logger.error(f"Failed to force kill VM: {e3}")
        try:
            run_command(f"multipass delete {vm_name} --purge")
        except Exception as e4:
            logger.warning(f"Failed to delete/purge instance (may not exist): {e4}")
        # Add additional cleanup for stuck processes
        try:
            subprocess.run(["pkill", "-f", "qemu-system-x86_64"], check=False)
            time.sleep(2)
        except Exception as e5:
            logger.warning(f"Failed to kill QEMU processes: {e5}")
        logger.info("Recovery steps complete. Continuing script.")
        return

def get_vm_ip():
    """Get the IP address of the VM"""
    ip_info = run_command(f"multipass info {vm_name} | grep IPv4", shell=True)
    return ip_info.split(':')[1].strip()

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
            # Add BatchMode=yes to SSH commands to prevent passphrase prompts
            if env is None:
                env = os.environ.copy()
            
            if 'ansible-playbook' in cmd:
                env['ANSIBLE_SSH_ARGS'] = '-o BatchMode=yes'
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

def generate_ssh_keys():
    """Generate SSH keys without passphrase"""
    logger.info("Generating SSH keys...")
    ssh_dir = Path.home() / '.ssh'
    key_path = ssh_dir / f'{vm_name}_key'
    
    # Generate new key without passphrase
    run_command(f"ssh-keygen -t ed25519 -f {key_path} -N ''", shell=True)
    logger.info("SSH keys generated successfully")

def check_ssh_keys():
    """Check if required SSH keys exist and generate if needed"""
    logger.info("Checking SSH keys...")
    ssh_dir = Path.home() / '.ssh'
    key_path = ssh_dir / f'{vm_name}_key'
    
    if not key_path.exists() or not key_path.with_suffix('.pub').exists():
        logger.info(f"SSH keys not found at {key_path}, generating new keys...")
        generate_ssh_keys()
    else:
        logger.info("SSH keys found and verified")

def force_kill_vm(vm_name):
    """Force kill the QEMU process for the given VM name"""
    logger.info(f"Force killing QEMU process for VM '{vm_name}' if running...")
    try:
        result = subprocess.run([
            "ps", "aux"
        ], capture_output=True, text=True, check=True)
        for line in result.stdout.splitlines():
            if "qemu-system-x86_64" in line and vm_name in line:
                pid = int(line.split()[1])
                logger.info(f"Killing QEMU process {pid} for VM '{vm_name}'")
                # Use sudo to kill if not running as root
                if os.geteuid() != 0:
                    subprocess.run(["sudo", "kill", "-9", str(pid)], check=True)
                else:
                    os.kill(pid, 9)
                logger.info(f"Successfully killed QEMU process {pid}")
                return True
        logger.info(f"No QEMU process found for VM '{vm_name}'")
        return False
    except Exception as e:
        logger.error(f"Error while force killing VM: {e}")
        return False

def setup_multipass():
    """Set up Multipass instance"""
    logger.info("Setting up Multipass instance...")
    
    # Check if instance exists and remove it
    try:
        force_kill_vm(vm_name)
        run_command(f"multipass -vvv delete {vm_name} --purge")
    except subprocess.CalledProcessError:
        pass
    
    # Launch new instance with retry logic for kvmvapic.bin error
    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempt {attempt + 1} of {max_retries} to launch Multipass instance...")
            run_command(f"multipass -vvv launch --name {vm_name} --memory 4G --disk 20G --cpus 2")
            logger.info("Multipass instance launched successfully!")
            break
        except subprocess.CalledProcessError as e:
            if "kvmvapic.bin" in str(e) and attempt < max_retries - 1:
                logger.warning(f"kvmvapic.bin error detected on attempt {attempt + 1}. Restarting Multipass daemon and retrying...")
                restart_multipass_daemon()
                # Additional cleanup before retry
                try:
                    subprocess.run(f"multipass delete {vm_name} --purge", shell=True, check=False, timeout=30)
                except Exception:
                    pass
                time.sleep(5)  # Wait before retry
            else:
                logger.error(f"Failed to launch Multipass instance after {max_retries} attempts")
                raise
    
    # Get instance IP
    ip_address = get_vm_ip()
    logger.info(f"Instance IP: {ip_address}")
    
    # Copy SSH key to instance
    run_command(f"multipass -vvv transfer {Path.home() / '.ssh' / f'{vm_name}_key.pub'} {vm_name}:")
    
    # Get initial user from inventory
    initial_user = get_initial_user()
    logger.info(f"Using initial user: {initial_user}")
    
    # Set up SSH in instance - combine commands to ensure atomic operation
    setup_ssh_cmd = f"""sudo mkdir -p /home/{initial_user}/.ssh && sudo cat /home/{initial_user}/{vm_name}_key.pub > /home/{initial_user}/.ssh/authorized_keys && sudo chown -R {initial_user}:{initial_user} /home/{initial_user}/.ssh && sudo chmod 700 /home/{initial_user}/.ssh && sudo chmod 600 /home/{initial_user}/.ssh/authorized_keys && sudo sed -i "s/^#\?PubkeyAuthentication.*/PubkeyAuthentication yes/" /etc/ssh/sshd_config && sudo sed -i "s/^#\?PasswordAuthentication.*/PasswordAuthentication no/" /etc/ssh/sshd_config && sudo systemctl restart ssh && echo "=== Debug Info ===" && ls -la /home/{initial_user}/.ssh && cat /home/{initial_user}/.ssh/authorized_keys && grep -i "PubkeyAuthentication" /etc/ssh/sshd_config && grep -i "PasswordAuthentication" /etc/ssh/sshd_config"""
    logger.info(f"SSH setup command: {setup_ssh_cmd}")
    run_command(f"multipass exec {vm_name} -- bash -c '{setup_ssh_cmd}'", shell=True)
    
    # Start ssh-agent and add the key
    logger.info("Setting up ssh-agent...")
    run_command("eval $(ssh-agent -s)", shell=True)
    run_command(f"ssh-add {Path.home() / '.ssh' / f'{vm_name}_key'}", shell=True)
    
    # Test SSH connection directly
    logger.info("Testing SSH connection...")
    test_ssh_cmd = f"ssh -v -o StrictHostKeyChecking=no {initial_user}@{ip_address} 'echo SSH connection successful'"
    run_command(test_ssh_cmd, shell=True)

def update_values_json():
    """Update values.json with new SSH key and IP"""
    logger.info("Updating values.json...")
    values_path = Path(__file__).parent.parent / '00utils' / 'values.json'
    
    # Get public key
    pub_key = run_command(f"cat {Path.home() / '.ssh' / f'{vm_name}_key.pub'}")
    
    # Get IP address
    ip_address = get_vm_ip()
    
    # Read and parse current values.json
    with open(values_path, 'r') as f:
        values = json.load(f)
    
    # Update SSH key and IP
    values['nodes'][vm_name]['ssh_public_key'] = pub_key
    values['nodes'][vm_name]['ip'] = ip_address
    
    # Write updated content
    with open(values_path, 'w') as f:
        json.dump(values, f, indent=4)

def get_initial_user():
    """Get the initial user from values.json"""
    values_path = Path(__file__).parent.parent / '00utils' / 'values.json'
    
    with open(values_path, 'r') as f:
        values = json.load(f)
    
    # Get initial user for the current VM
    initial_user = values['nodes'][vm_name]['user']['initial']
    return initial_user

def update_values_json_with_wg_key():
    """Update values.json with new SSH key, IP, and WireGuard public key"""
    logger.info("Updating values.json with WireGuard public key...")
    values_path = Path(__file__).parent.parent / '00utils' / 'values.json'
    
    # Get public key
    pub_key = run_command(f"cat {Path.home() / '.ssh' / f'{vm_name}_key.pub'}")
    
    # Get IP address
    ip_address = get_vm_ip()
    
    # Try to get server WireGuard public key (optional, may not exist yet)
    vm_ip = get_vm_ip()
    initial_user = get_initial_user()
    ssh_cmd = f"ssh {initial_user}@{vm_ip} -i {Path.home() / '.ssh' / f'{vm_name}_key'}"
    try:
        server_wg_pub_key = run_command(f"{ssh_cmd} 'sudo cat /etc/wireguard/server_public.key'", shell=True)
        logger.info("WireGuard public key found and will be updated in values.json")
    except subprocess.CalledProcessError:
        logger.info("WireGuard public key not found yet (WireGuard not set up), skipping WireGuard key update")
        server_wg_pub_key = None
    
    # Read and parse current values.json
    with open(values_path, 'r') as f:
        values = json.load(f)
    
    # Update SSH key and IP
    values['nodes'][vm_name]['ssh_public_key'] = pub_key
    values['nodes'][vm_name]['ip'] = ip_address
    
    # Update WireGuard public key only if it exists
    if server_wg_pub_key:
        values['wireguard']['nodes']['vault']['public_key'] = server_wg_pub_key
    
    # Write updated content
    with open(values_path, 'w') as f:
        json.dump(values, f, indent=4)

def run_playbook(playbook):
    logger.info(f"Running playbook: {playbook}")
    # Set environment variables for Ansible to use the stored password
    env = os.environ.copy()
    env['ANSIBLE_BECOME_PASSWORD'] = sudo_password
    env['ANSIBLE_SSH_ARGS'] = '-o BatchMode=yes'
    
    # Run ansible-playbook with vm_name as extra variable
    run_command(f"ansible-playbook -i inventory.ini {playbook} -e vm_name={vm_name}", interactive=True, env=env)

def setup_wireguard():
    """Set up WireGuard configuration"""
    logger.info("Setting up WireGuard...")
    
    # Get client public key
    client_pub_key = run_sudo_command("cat /etc/wireguard/client_public.key")
    
    # Get VM IP
    vm_ip = get_vm_ip()
    
    # SSH into server and update WireGuard config
    wg_config = f"""[Interface]
Address = 10.0.0.1/24
ListenPort = 51820
PrivateKey = {run_command(f"ssh {vm_name}_user@{vm_ip} -i {Path.home() / '.ssh' / f'{vm_name}_key'} 'sudo cat /etc/wireguard/server_private.key'", shell=True)}

[Peer]
PublicKey = {client_pub_key}
AllowedIPs = 10.0.0.2/32
"""
    ssh_cmd = f"ssh {vm_name}_user@{vm_ip} -i {Path.home() / '.ssh' / f'{vm_name}_key'}"
    
    # First, ensure the config file exists and has proper format
    run_command(f"{ssh_cmd} 'sudo touch /etc/wireguard/wg0.conf'", shell=True)
    run_command(f"{ssh_cmd} 'sudo chmod 600 /etc/wireguard/wg0.conf'", shell=True)
    
    # Add the complete configuration
    run_command(f"{ssh_cmd} 'echo \"{wg_config}\" | sudo tee /etc/wireguard/wg0.conf'", shell=True)
    
    # Restart WireGuard
    run_command(f"{ssh_cmd} 'sudo wg-quick down wg0 || true'", shell=True)
    run_command(f"{ssh_cmd} 'sudo wg-quick up wg0'", shell=True)
    
    # Update local WireGuard config
    server_pub_key = run_command(f"{ssh_cmd} 'sudo cat /etc/wireguard/server_public.key'", shell=True)
    local_config = f"""[Interface]
PrivateKey = {run_sudo_command("cat /etc/wireguard/client_private.key")}
Address = 10.0.0.2/24
DNS = 1.1.1.1

[Peer]
PublicKey = {server_pub_key}
Endpoint = {vm_ip}:51820
AllowedIPs = 10.0.0.0/24
PersistentKeepalive = 25
"""
    # Ensure local config file exists and has proper permissions
    run_sudo_command("touch /etc/wireguard/wg0.conf")
    run_sudo_command("chmod 600 /etc/wireguard/wg0.conf")
    
    # Update local config
    run_sudo_tee(local_config, "/etc/wireguard/wg0.conf")
    
    # Restart local WireGuard
    run_sudo_command("wg-quick down wg0 || true")
    run_sudo_command("wg-quick up wg0")
    
    # Update values.json with WireGuard public key
    update_values_json_with_wg_key()

def test_vpn_connection():
    """Test VPN connection"""
    logger.info("Testing VPN connection...")
    
    # Remove old host key
    run_command("ssh-keygen -R 10.0.0.1")
    
    # Test SSH connection with automatic host key acceptance
    try:
        run_command(f"ssh -o StrictHostKeyChecking=no {vm_name}_user@10.0.0.1 -i {Path.home() / '.ssh' / f'{vm_name}_key'} 'echo \"VPN connection successful\"'", shell=True)
        logger.info("VPN connection test successful!")
    except subprocess.CalledProcessError as e:
        logger.error("VPN connection test failed!")
        raise

def is_fatal_error(e):
    """Return True if the error is fatal, False if it is a known non-fatal error."""
    non_fatal_patterns = [
        "Vault is already initialized",
        "Could not find the requested service vault: host",
        "command terminated with exit code 2",
        # Add more patterns as needed
    ]
    msg = str(e)
    for pat in non_fatal_patterns:
        if pat in msg:
            return False
    return True

def manual_multipass_recovery():
    """Manual recovery function for Multipass issues, especially kvmvapic.bin errors"""
    logger.info("Starting manual Multipass recovery...")
    
    # Stop all instances
    try:
        subprocess.run(["multipass", "stop", "--all"], check=False, timeout=30)
        logger.info("Stopped all instances")
    except Exception as e:
        logger.warning(f"Failed to stop instances: {e}")
    
    # Kill all QEMU processes
    try:
        subprocess.run(["sudo", "pkill", "-f", "qemu-system-x86_64"], check=False)
        time.sleep(3)
        logger.info("Killed QEMU processes")
    except Exception as e:
        logger.warning(f"Failed to kill QEMU processes: {e}")
    
    # Unload and reload the Multipass daemon
    try:
        subprocess.run([
            "sudo", "launchctl", "unload", "/Library/LaunchDaemons/com.canonical.multipassd.plist"
        ], check=False)
        time.sleep(5)
        subprocess.run([
            "sudo", "launchctl", "load", "/Library/LaunchDaemons/com.canonical.multipassd.plist"
        ], check=False)
        time.sleep(10)
        logger.info("Reloaded Multipass daemon")
    except Exception as e:
        logger.error(f"Failed to reload daemon: {e}")
    
    # Clean up any stale instance data
    try:
        multipass_data_dir = "/var/root/Library/Application Support/multipassd/qemu/vault/instances"
        if os.path.exists(multipass_data_dir):
            for item in os.listdir(multipass_data_dir):
                if item != "multipassd.log":
                    subprocess.run(["sudo", "rm", "-rf", f"{multipass_data_dir}/{item}"], check=False)
        logger.info("Cleaned up stale instance data")
    except Exception as e:
        logger.warning(f"Failed to clean up data: {e}")
    
    # Test Multipass functionality
    try:
        result = subprocess.run(["multipass", "list"], check=True, capture_output=True, text=True, timeout=10)
        logger.info("Multipass is working correctly")
        logger.info(f"Current instances: {result.stdout}")
    except Exception as e:
        logger.error(f"Multipass test failed: {e}")
    
    logger.info("Manual recovery complete. Try running your setup script again.")

def generate_dynamic_inventory():
    """Generate a dynamic inventory file based on vm_name"""
    logger.info(f"Generating dynamic inventory for {vm_name}...")
    
    # Get the current playbook directory
    playbook_dir = str(Path(__file__).parent.absolute())
    
    inventory_content = f"""[{vm_name}_initial]
{vm_name}_initial_host ansible_host="{{{{ lookup('file', '../00utils/values.json') | from_json | json_query('nodes.{vm_name}.ip') }}}}" ansible_user=ubuntu ansible_ssh_private_key_file=~/.ssh/{vm_name}_key ansible_ssh_common_args='-o BatchMode=yes -o StrictHostKeyChecking=no'

[{vm_name}_public]
{vm_name}_public_host ansible_host="{{{{ lookup('file', '../00utils/values.json') | from_json | json_query('nodes.{vm_name}.ip') }}}}" ansible_user="{{{{ lookup('file', '../00utils/values.json') | from_json | json_query('nodes.{vm_name}.user.public') }}}}" ansible_ssh_private_key_file=~/.ssh/{vm_name}_key ansible_ssh_common_args='-o BatchMode=yes -o StrictHostKeyChecking=no'

[{vm_name}_private]
{vm_name} ansible_host="{{{{ lookup('file', '../00utils/values.json') | from_json | json_query('wireguard.network.vault_server.ip') }}}}" ansible_user="{{{{ lookup('file', '../00utils/values.json') | from_json | json_query('nodes.{vm_name}.user.public') }}}}" ansible_ssh_private_key_file=~/.ssh/{vm_name}_key ansible_ssh_common_args='-o BatchMode=yes -o StrictHostKeyChecking=no'

[all:vars]
vm_name="{vm_name}"
playbook_dir="{playbook_dir}"
server_private_key="{{{{ lookup('file', 'wireguard/values/server_private.txt') | trim }}}}"
server_port="{{{{ lookup('file', '../00utils/values.json') | from_json | json_query('wireguard.network.vault_server.listen_port') }}}}"
new_user="{{{{ lookup('file', '../00utils/values.json') | from_json | json_query('nodes.{vm_name}.user.public') }}}}"
initial_user="{{{{ lookup('file', '../00utils/values.json') | from_json | json_query('nodes.{vm_name}.user.initial') }}}}"

# SSH Public Keys
ssh_keys_{vm_name}="{{{{ lookup('file', '../00utils/values.json') | from_json | json_query('nodes.{vm_name}.ssh_public_key') }}}}"
"""
    
    inventory_path = Path(__file__).parent / 'inventory.ini'
    with open(inventory_path, 'w') as f:
        f.write(inventory_content)
    
    logger.info(f"Dynamic inventory generated for {vm_name}")

def run_sudo_command(cmd):
    """Run a sudo command with the stored password"""
    logger.info(f"Running sudo command: {cmd}")
    try:
        # Use echo to pipe the password to sudo
        full_cmd = f"echo '{sudo_password}' | sudo -S {cmd}"
        process = subprocess.run(full_cmd, shell=True, check=True, capture_output=True, text=True, timeout=180)
        logger.info(f"Command output: {process.stdout}")
        return process.stdout.strip()
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out after 180 seconds: {cmd}")
        raise
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e.stderr}")
        raise

def run_sudo_tee(content, filepath):
    """Write content to a file using sudo tee"""
    logger.info(f"Writing content to {filepath} using sudo")
    try:
        # Use echo to pipe content to sudo tee
        full_cmd = f"echo '{content}' | sudo -S tee {filepath} > /dev/null"
        process = subprocess.run(full_cmd, shell=True, check=True, capture_output=True, text=True, timeout=180)
        logger.info(f"Successfully wrote to {filepath}")
        return process.stdout.strip()
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out after 180 seconds: tee to {filepath}")
        raise
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e.stderr}")
        raise

def main():
    try:
        logger.info("Starting server setup process...")
        os.chdir(Path(__file__).parent)
        # Step index mapping
        steps = [
            ("multipass_auth", check_multipass_auth),
            ("ssh_keys", check_ssh_keys),
            ("multipass_setup", setup_multipass),
            ("update_values_json", update_values_json_with_wg_key),
            ("generate_inventory", generate_dynamic_inventory),
            ("playbook_00", lambda: run_playbook("00_ssh_for_new_user.yml")),
            ("playbook_01", lambda: run_playbook("01_configure_security.yml")),
            ("playbook_02", lambda: run_playbook("02_setup_k3s.yml")),
            ("playbook_03", lambda: run_playbook("03_setup_and_config_wg.yml")),
            ("wireguard_setup", setup_wireguard),
            ("vpn_test", test_vpn_connection),
            ("playbook_05", lambda: run_playbook("05_setup_firewall.yml")),
            ("playbook_06", lambda: run_playbook("06_harden_firewall.yml")),
            ("playbook_07", lambda: run_playbook("07_vault_initial_setup.yml")),
            ("playbook_08", lambda: run_playbook("08_store_vault_keys.yml")),
            ("playbook_09", lambda: run_playbook("09_verify_prerequisites.yml")),
            ("playbook_10", lambda: run_playbook("10_setup_unseal_scripts.yml")),
            ("playbook_11", lambda: run_playbook("11_configure_vault_auth.yml")),
            ("playbook_12", lambda: run_playbook("12_configure_flask_vault_access.yml")),
        ]
        # Map menu choice to step index
        step_start_map = list(range(len(menu_options)))
        start_idx = step_start_map[start_choice]

        # If "Start from the very beginning", run all steps
        if start_idx == 0:
            run_range = range(len(steps))
        else:
            run_range = range(start_idx - 1, len(steps))

        # Run steps from the selected point
        for i in run_range:
            logger.info(f"Running step: {steps[i][0]}")
            try:
                steps[i][1]()
            except Exception as e:
                logger.error(f"Step failed: {str(e)}")
                if is_fatal_error(e):
                    logger.error("Fatal error encountered. Exiting.")
                    sys.exit(1)
                else:
                    logger.warning("Non-fatal error. Continuing to next step.")

        logger.info("Server setup completed successfully!")

    except Exception as e:
        logger.error(f"Setup failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    # Add option to run manual recovery
    if len(sys.argv) > 1 and sys.argv[1] == "--recover":
        manual_multipass_recovery()
    else:
        main() 