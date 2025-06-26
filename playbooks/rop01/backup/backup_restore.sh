#!/bin/bash

# VPS Backup and Restore Script using Restic
# This script backs up all critical VPS configurations and can restore them

set -e

# Configuration - Auto-detect project username
PROJECT_USER=$(getent passwd | awk -F: '$3 >= 1000 && $3 < 65534 {print $1}' | head -1)
BACKUP_NAME="${PROJECT_USER}-vps-backup"
RESTIC_REPO="/backup/restic-repo"
BACKUP_PATHS=(
    "/etc/rancher"
    "/var/lib/rancher"
    "/etc/wireguard"
    "/home"
    "/root"
    "/etc/ssh"
    "/etc/systemd/system"
    "/var/lib/kubelet"
    "/var/lib/cni"
    "/etc/fail2ban"
    "/etc/ntp.conf"
    "/etc/hosts"
    "/etc/resolv.conf"
    "/etc/fstab"
    "/etc/crontab"
    "/var/spool/cron"
    "/etc/passwd"
    "/etc/group"
    "/etc/shadow"
    "/etc/gshadow"
    "/etc/sudoers"
    "/etc/sudoers.d"
    "/etc/ssh/sshd_config"
    "/etc/ssh/ssh_config"
    "/etc/ssh/ssh_host_*"
    "/etc/ssl/certs"
    "/etc/ssl/private"
    "/var/lib/ssl-cert"
    "/etc/letsencrypt"
    "/var/lib/letsencrypt"
    "/etc/nginx"
    "/var/log/nginx"
    "/etc/apache2"
    "/var/log/apache2"
    "/etc/mysql"
    "/var/lib/mysql"
    "/etc/postgresql"
    "/var/lib/postgresql"
    "/etc/redis"
    "/var/lib/redis"
    "/etc/vault"
    "/var/lib/vault"
    "/etc/consul"
    "/var/lib/consul"
    "/etc/nomad"
    "/var/lib/nomad"
    "/etc/traefik"
    "/var/lib/traefik"
    "/etc/prometheus"
    "/var/lib/prometheus"
    "/etc/grafana"
    "/var/lib/grafana"
    "/etc/alertmanager"
    "/var/lib/alertmanager"
    "/etc/node_exporter"
    "/etc/cadvisor"
    "/etc/fluentd"
    "/var/lib/fluentd"
    "/etc/elasticsearch"
    "/var/lib/elasticsearch"
    "/etc/kibana"
    "/var/lib/kibana"
    "/etc/logstash"
    "/var/lib/logstash"
    "/etc/filebeat"
    "/var/lib/filebeat"
    "/etc/metricbeat"
    "/var/lib/metricbeat"
    "/etc/packetbeat"
    "/var/lib/packetbeat"
    "/etc/heartbeat"
    "/var/lib/heartbeat"
    "/etc/auditbeat"
    "/var/lib/auditbeat"
    "/etc/functionbeat"
    "/var/lib/functionbeat"
    "/etc/journalbeat"
    "/var/lib/journalbeat"
    "/etc/winlogbeat"
    "/var/lib/winlogbeat"
    "/etc/cloudwatch"
    "/var/lib/cloudwatch"
    "/etc/stackdriver"
    "/var/lib/stackdriver"
    "/etc/datadog"
    "/var/lib/datadog"
    "/etc/newrelic"
    "/var/lib/newrelic"
    "/etc/splunk"
    "/var/lib/splunk"
    "/etc/sumo"
    "/var/lib/sumo"
    "/etc/loggly"
    "/var/lib/loggly"
    "/etc/papertrail"
    "/var/lib/papertrail"
    "/etc/logentries"
    "/var/lib/logentries"
    "/etc/logzio"
    "/var/lib/logzio"
    "/etc/logmatic"
    "/var/lib/logmatic"
    "/etc/logsene"
    "/var/lib/logsene"
    "/etc/logdna"
    "/var/lib/logdna"
    "/etc/logflare"
    "/var/lib/logflare"
    "/etc/logtail"
    "/var/lib/logtail"
)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

install_restic() {
    log_info "Installing Restic..."
    if ! command -v restic &> /dev/null; then
        # Download and install restic
        wget -O /tmp/restic.bz2 https://github.com/restic/restic/releases/latest/download/restic_linux_amd64.bz2
        bunzip2 /tmp/restic.bz2
        chmod +x /tmp/restic
        mv /tmp/restic /usr/local/bin/
        log_success "Restic installed successfully"
    else
        log_info "Restic is already installed"
    fi
}

init_repo() {
    log_info "Initializing Restic repository..."
    if [ ! -d "$RESTIC_REPO" ]; then
        mkdir -p "$RESTIC_REPO"
    fi
    
    if ! restic -r "$RESTIC_REPO" snapshots &> /dev/null; then
        restic -r "$RESTIC_REPO" init
        log_success "Restic repository initialized"
    else
        log_info "Restic repository already exists"
    fi
}

backup_vps() {
    log_info "Starting VPS backup..."
    
    # Create backup directory
    mkdir -p /tmp/vps-backup
    
    # Create system info file
    cat > /tmp/vps-backup/system-info.txt << EOF
VPS Backup Information
======================
Date: $(date)
Hostname: $(hostname)
OS: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)
Kernel: $(uname -r)
Architecture: $(uname -m)
CPU: $(nproc) cores
Memory: $(free -h | grep Mem | awk '{print $2}')
Disk: $(df -h / | tail -1 | awk '{print $2}')
Uptime: $(uptime -p)

Installed Packages:
$(dpkg -l | grep -E '^(ii|hi)' | wc -l) packages installed

Kubernetes Status:
$(kubectl version --short 2>/dev/null || echo "Kubernetes not available")

WireGuard Status:
$(wg show 2>/dev/null || echo "WireGuard not available")

SSH Status:
$(systemctl is-active ssh 2>/dev/null || echo "SSH not available")

EOF

    # Backup system info
    restic -r "$RESTIC_REPO" backup /tmp/vps-backup/system-info.txt --tag "$BACKUP_NAME"
    
    # Backup critical paths
    for path in "${BACKUP_PATHS[@]}"; do
        if [ -e "$path" ]; then
            log_info "Backing up: $path"
            restic -r "$RESTIC_REPO" backup "$path" --tag "$BACKUP_NAME"
        else
            log_warning "Path does not exist: $path"
        fi
    done
    
    # Create a comprehensive backup snapshot
    log_info "Creating comprehensive backup snapshot..."
    restic -r "$RESTIC_REPO" backup /tmp/vps-backup --tag "$BACKUP_NAME"
    
    # Clean up
    rm -rf /tmp/vps-backup
    
    log_success "VPS backup completed successfully!"
    
    # Show backup info
    log_info "Backup snapshots:"
    restic -r "$RESTIC_REPO" snapshots --tag "$BACKUP_NAME"
}

restore_vps() {
    log_info "Starting VPS restore..."
    
    # Get the latest snapshot
    LATEST_SNAPSHOT=$(restic -r "$RESTIC_REPO" snapshots --tag "$BACKUP_NAME" --json | jq -r '.[-1].id')
    
    if [ -z "$LATEST_SNAPSHOT" ]; then
        log_error "No backup snapshots found"
        exit 1
    fi
    
    log_info "Restoring from snapshot: $LATEST_SNAPSHOT"
    
    # Restore system configurations
    for path in "${BACKUP_PATHS[@]}"; do
        if restic -r "$RESTIC_REPO" list "$LATEST_SNAPSHOT" | grep -q "$path"; then
            log_info "Restoring: $path"
            restic -r "$RESTIC_REPO" restore "$LATEST_SNAPSHOT" --target / --include "$path"
        fi
    done
    
    # Restart services
    log_info "Restarting services..."
    systemctl daemon-reload
    systemctl restart ssh
    systemctl restart k3s 2>/dev/null || true
    systemctl restart wireguard 2>/dev/null || true
    
    log_success "VPS restore completed successfully!"
}

list_backups() {
    log_info "Available backups:"
    restic -r "$RESTIC_REPO" snapshots --tag "$BACKUP_NAME"
}

cleanup_old_backups() {
    log_info "Cleaning up old backups (keeping last 7 days)..."
    restic -r "$RESTIC_REPO" forget --tag "$BACKUP_NAME" --keep-daily 7 --prune
    log_success "Cleanup completed"
}

# Main script
case "$1" in
    "backup")
        check_root
        install_restic
        init_repo
        backup_vps
        ;;
    "restore")
        check_root
        install_restic
        restore_vps
        ;;
    "list")
        install_restic
        list_backups
        ;;
    "cleanup")
        check_root
        install_restic
        cleanup_old_backups
        ;;
    "init")
        check_root
        install_restic
        init_repo
        ;;
    *)
        echo "VPS Backup and Restore Script"
        echo "Usage: $0 {backup|restore|list|cleanup|init}"
        echo ""
        echo "Commands:"
        echo "  backup   - Create a complete backup of the VPS"
        echo "  restore  - Restore the VPS from the latest backup"
        echo "  list     - List available backups"
        echo "  cleanup  - Clean up old backups (keep last 7 days)"
        echo "  init     - Initialize the backup repository"
        echo ""
        echo "Examples:"
        echo "  $0 backup    # Create backup"
        echo "  $0 restore   # Restore from backup"
        echo "  $0 list      # Show available backups"
        exit 1
        ;;
esac 