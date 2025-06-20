# Server Setup Process Documentation

This document outlines the automated server setup process implemented in `setup_server.py`. The script automates the creation and configuration of a Multipass VM with WireGuard VPN and SSH access.

## Prerequisites

- Multipass installed on the local machine
- SSH keys generated for the VM (should be named `{vm_name}_key` and `{vm_name}_key.pub`)
- Ansible installed on the local machine
- Sudo access on the local machine

## Process Overview

1. **Initial Setup**
   - Creates a log directory and configures logging
   - Prompts for VM name
   - Sets up logging with both file and console output

2. **Multipass Authentication** (currently commented out)
   - Checks Multipass authentication status
   - Handles authentication if required
   - Sets up passphrase for Multipass

3. **VM Setup** (currently commented out)
   - Removes existing VM instance if present
   - Launches new Multipass instance with:
     - 4GB RAM
     - 20GB disk
     - 2 CPUs
   - Copies SSH public key to the VM
   - Configures SSH access on the VM

4. **Configuration Updates**
   - Updates `values.json` with:
     - New SSH public key
     - VM's IP address

5. **Ansible Playbook Execution**
   - Runs the following playbooks in sequence:
     1. `00_ssh_for_new_user.yml` - Sets up SSH for new user
     2. `01_configure_security.yml` - Configures security settings
     3. `02_setup_k3s.yml` - Sets up K3s
     4. `03_setup_and_config_wg.yml` - Configures WireGuard

6. **WireGuard Configuration**
   - Sets up WireGuard on both server and client
   - Configures server-side WireGuard:
     - Creates interface configuration
     - Sets up peer configuration
     - Configures IP addressing (10.0.0.1/24)
   - Configures client-side WireGuard:
     - Sets up interface configuration
     - Configures peer settings
     - Sets up DNS (1.1.1.1)
     - Configures persistent keepalive

7. **Connection Testing**
   - Removes old host key for 10.0.0.1
   - Tests SSH connection through WireGuard VPN
   - Verifies successful connection

## Current Configuration

The script is currently configured to:
- Skip the initial Multipass and VM setup steps
- Focus on WireGuard configuration and testing
- Use dynamic VM naming for all operations

## Usage

1. Run the script:
   ```bash
   python3 setup_server.py
   ```

2. Enter the VM name when prompted

3. Enter sudo password when required

## Important Notes

- The script creates a new log file for each run in the `logs` directory
- SSH keys must be pre-generated and named according to the VM name
- The WireGuard configuration uses the 10.0.0.0/24 subnet
- Server is configured as 10.0.0.1
- Client is configured as 10.0.0.2

## Troubleshooting

If the setup fails:
1. Check the log file in the `logs` directory
2. Verify SSH keys exist and are properly named
3. Ensure Multipass is running and accessible
4. Check WireGuard configuration files on both server and client
5. Verify network connectivity and firewall settings

## Security Considerations

- SSH keys are required for authentication
- WireGuard provides encrypted VPN tunnel
- Proper file permissions are set for configuration files
- Sudo access is required for certain operations 