# Values.json Usage Documentation

This document tracks all usages of variables from `values.json` across the codebase.

## Current Values in values.json

```json
{
    "nodes": {
        "rop01": {
            "ssh_public_key": "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIN7Q1KeY1UynaqtZXgjMeB2jTN1twL9Fa1hgD7TWrV3a sil@Sil-Macbook.local",
            "user": {
                "public": "rop01_user"
            }
        }
    },
    "wireguard": {
        "network": {
            "vault_server": {
                "ip": "10.0.0.1",
                "listen_port": 51820
            }
        }
    }
}
```

## Usage Locations

### 1. nodes.rop01.ip
- **File**: `inventory.ini`
- **Usage**: Used in two places:
  1. `rop01_initial_host` ansible_host value
  2. `rop01_public_host` ansible_host value
- **Purpose**: Sets the IP address for initial and public host configurations

### 2. nodes.rop01.user.public
- **File**: `inventory.ini`
- **Usage**: Used in two places:
  1. `rop01_public_host` ansible_user value
  2. `new_user` variable definition
- **Purpose**: Defines the username for SSH access and user operations

### 3. nodes.rop01.ssh_public_key
- **File**: `inventory.ini`
- **Usage**: Used in `ssh_keys_rop01` variable definition
- **Purpose**: Sets the SSH public key for authentication

### 4. wireguard.network.vault_server.ip
- **File**: `inventory.ini`
- **Usage**: Used in `rop01` ansible_host value under `[rop01_private]` section
- **Purpose**: Sets the WireGuard IP address for the vault server

### 5. wireguard.network.vault_server.listen_port
- **File**: `inventory.ini`
- **Usage**: Used in `server_port` variable definition
- **Purpose**: Defines the WireGuard listening port for the vault server

## Playbook Dependencies

The following playbooks depend on these values:

1. `00_ssh_for_new_user.yml`
   - Uses: `new_user`, `ssh_keys_rop01`
   - Purpose: Sets up SSH access for the new user

2. `02_setup_k3s.yml`
   - Uses: `new_user`
   - Purpose: Configures K3s with proper user permissions

3. `03_setup_and_config_wg.yml`
   - Uses: `server_port`
   - Purpose: Sets up WireGuard configuration

4. `05_setup_firewall.yml`
   - Uses: `server_port`
   - Purpose: Configures firewall rules for WireGuard

## Notes

- All values are accessed through Ansible's `lookup` and `json_query` functions
- The values are primarily used for configuration of:
  - SSH access
  - User management
  - WireGuard networking
  - Firewall rules
- No values are currently used in template files (`.j2`) 