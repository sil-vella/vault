# VPS Backup and Restore Guide

## 🎯 **Overview**

This guide provides comprehensive backup and restore functionality for your VPS infrastructure. The system includes both **local orchestration** (runs from your Mac) and **remote execution** (runs on VPS) components.

**Key Features:**
- ✨ **One-command backup from local machine**
- 📊 **Local log capture** with timestamped files
- 🔥 **Complete firewall rules backup** (iptables + UFW)
- 🧹 **Automatic cleanup** and file management
- 🔄 **Cross-server migration support**

## 📦 **What Gets Backed Up (19 Critical Components)**

### **Kubernetes Infrastructure:**
- `/etc/rancher` - K3s configuration
- `/var/lib/rancher` - Main K3s data store (~1.3GB)
- `/var/lib/kubelet` - Kubelet runtime data
- `/var/lib/cni` - Container networking

### **Network & Security:**
- `/etc/wireguard` - WireGuard VPN configurations
- `/etc/iptables` - **IPv4 & IPv6 firewall rules** 🔥
- `/etc/ufw` - **UFW firewall configuration** 🔥
- `/etc/fail2ban` - Security monitoring
- `/etc/ssh` - SSH server configurations

### **User Data & System:**
- `/home` - **Complete user home directories**
- `/root` - **Root user data and configurations**
- `/etc/systemd/system` - Custom system services
- `/etc/passwd`, `/etc/group`, `/etc/shadow` - User accounts
- `/etc/sudoers`, `/etc/sudoers.d` - Sudo permissions
- `/etc/hosts`, `/etc/resolv.conf` - Network configuration

## 🚀 **Quick Commands (Local Orchestrator)**

### **From your Mac (in playbooks/rop02 directory):**

```bash
# Create backup and download locally
./backup/local_backup_orchestrator.sh backup

# List all backups and logs
./backup/local_backup_orchestrator.sh list

# Restore VPS from local backup
./backup/local_backup_orchestrator.sh restore

# Clean up old files (keep last 5)
./backup/local_backup_orchestrator.sh cleanup

# Show configuration
./backup/local_backup_orchestrator.sh config
```

## ⚙️ **Configuration**

### **Local Orchestrator Settings:**
Edit only these two variables in `local_backup_orchestrator.sh`:
```bash
PROJECT_NAME="rop02"      # Your project name
VPS_IP="10.0.0.3"        # Your VPS IP address
```

**Everything else is auto-derived:**
- VPS User: `root` (or `$PROJECT_NAME` for non-root)
- SSH Key: `~/.ssh/rop02_key`
- Local Backup Dir: `./backup/backups`
- Remote Backup Dir: `/backup/vps-config`

## 📋 **Complete Workflow**

### **1. Prerequisites**
```bash
# Ensure WireGuard VPN is active
sudo wg-quick up wg0

# Verify VPS connectivity
ping 10.0.0.3
```

### **2. First-Time Setup**
The orchestrator automatically:
- Tests SSH connectivity
- Deploys backup script to VPS
- Sets up required directories

### **3. Backup Process**
```bash
./backup/local_backup_orchestrator.sh backup
```

**What happens:**
1. 🔍 **Configuration check** - Verifies SSH, IP, and keys
2. 📤 **Script deployment** - Ensures latest backup script on VPS
3. 🔄 **Remote backup execution** - Runs backup on VPS with sudo
4. 📊 **Local log capture** - Saves all output to timestamped log file
5. ⬇️ **File download** - Downloads backup to local machine
6. 🧹 **Remote cleanup** - Deletes backup from VPS to save space

### **4. Backup Results**
- **Backup file**: `./backup/backups/YYYYMMDD_HHMMSS.tar.gz` (~580MB)
- **Log file**: `./backup/backups/backup_rop02_YYYYMMDD_HHMMSS.log`
- **Compression**: 1.4GB → 580MB (~59% reduction)

## 🔄 **Migration to New VPS**

### **Step 1: Backup Current VPS**
```bash
./backup/local_backup_orchestrator.sh backup
```

### **Step 2: Update Configuration**
```bash
# Edit local_backup_orchestrator.sh
VPS_IP="NEW_VPS_IP"  # Change to new VPS IP
```

### **Step 3: Restore on New VPS**
```bash
./backup/local_backup_orchestrator.sh restore
```

**The script automatically:**
- Uploads latest local backup to new VPS
- Executes restore process
- Restarts all services
- Cleans up uploaded files

## 🔥 **Critical Firewall Protection**

### **Now Includes Complete Firewall Backup:**
- **iptables rules** (`/etc/iptables/rules.v4` & `rules.v6`)
- **UFW configuration** (complete `/etc/ufw/` directory)

### **Protected Rules Include:**
- 🔐 **Kubernetes networking** (KUBE-ROUTER, KUBE-PROXY chains)
- 🌐 **WireGuard VPN access** (UDP 51820)
- 🔑 **SSH access controls** (TCP 22)
- 🏛️ **Vault API permissions** (TCP 8200)
- 🛡️ **Network policies** and security chains

**Without firewall backup, restoration would leave your VPS vulnerable!**

## 📊 **File Management**

### **Automatic Cleanup:**
```bash
./backup/local_backup_orchestrator.sh cleanup
```
- Keeps last **5 backup files**
- Keeps last **5 log files**
- Removes older files automatically

### **List All Files:**
```bash
./backup/local_backup_orchestrator.sh list
```
Shows:
- Local backup files with sizes
- Local log files with timestamps
- Remote backups on VPS (if any)

## 📈 **Monitoring & Logs**

### **Local Log Files:**
- **Location**: `./backup/backups/backup_rop02_YYYYMMDD_HHMMSS.log`
- **Content**: Complete SSH session output
- **Includes**: System info, file sizes, success/failure status
- **Benefits**: No remote file creation complexity

### **Log Analysis:**
```bash
# View latest backup log
ls -t ./backup/backups/*.log | head -1 | xargs cat

# Check for errors
grep -i error ./backup/backups/*.log

# View backup summary
grep "Backup summary" ./backup/backups/*.log
```

## ⚠️ **Important Notes**

### **Requirements:**
- **WireGuard VPN** must be active (`sudo wg-quick up wg0`)
- **SSH key** must be configured (`~/.ssh/rop02_key`)
- **VPS user** must have sudo privileges (passwordless recommended)

### **Cross-Server Compatibility:**
The backup scripts now **auto-detect usernames**, but if moving between different server setups, verify:
- User account structure
- Sudo permissions
- SSH key access

### **Security:**
- Backups include `/etc/shadow` (password hashes)
- SSH keys and certificates included
- Firewall rules preserve security policies
- Keep backup files secure on local machine

## 🔧 **Troubleshooting**

### **Connection Issues:**
```bash
# Check WireGuard status
sudo wg show

# Test SSH connectivity
ssh -i ~/.ssh/rop02_key root@10.0.0.3 "echo 'Connection OK'"

# Verify configuration
./backup/local_backup_orchestrator.sh config
```

### **Backup Issues:**
```bash
# Check disk space on VPS
ssh -i ~/.ssh/rop02_key root@10.0.0.3 "df -h"

# Check local disk space
df -h .

# View recent logs
tail -50 ./backup/backups/*.log | tail -50
```

### **Restore Issues:**
```bash
# Verify backup integrity
tar -tzf ./backup/backups/LATEST_BACKUP.tar.gz | head -20

# Check service status after restore
ssh -i ~/.ssh/rop02_key root@10.0.0.3 "systemctl status k3s ssh"
```

## 📈 **Automation Options**

### **Scheduled Backups:**
```bash
# Add to local crontab for daily backups
echo "0 2 * * * cd /path/to/playbooks/rop02 && ./backup/local_backup_orchestrator.sh backup" | crontab -

# Weekly cleanup
echo "0 3 * * 0 cd /path/to/playbooks/rop02 && ./backup/local_backup_orchestrator.sh cleanup" | crontab -
```

## 🎉 **Success Indicators**

### **After Successful Backup:**
- ✅ **19 items backed up, 0 items skipped**
- ✅ Backup file ~580MB in `./backup/backups/`
- ✅ Log file created with complete session output
- ✅ Remote VPS cleaned up automatically
- ✅ All firewall rules included

### **After Successful Restore:**
- ✅ SSH access works to restored VPS
- ✅ WireGuard tunnel operational
- ✅ Kubernetes cluster running (`kubectl get nodes`)
- ✅ All services active (`systemctl status k3s ssh`)
- ✅ Firewall rules active (`iptables -L`)

## 🔄 **Backup Evolution Summary**

### **What We've Improved:**
1. **Local orchestration** - No more manual SSH commands
2. **Firewall inclusion** - Complete iptables + UFW backup
3. **Local log capture** - No remote file creation issues
4. **Auto-cleanup** - Keeps VPS storage clean
5. **Error handling** - Comprehensive checks at each step
6. **File management** - Organized backup and log retention

### **From 17 → 19 Backed Up Items:**
- Added `/etc/iptables` (firewall rules)
- Added `/etc/ufw` (UFW configuration)

---

**Last Updated**: June 26, 2025  
**Version**: 2.0  
**Tested On**: Ubuntu 24.04.2 LTS with K3s, WireGuard, iptables, UFW  
**Orchestrator**: macOS with WireGuard VPN connection 