#!/bin/bash

# Simple VPS Backup and Restore Script
# Focuses on critical configurations only

set -e

# Configuration - Auto-detect project username
PROJECT_USER=$(getent passwd | awk -F: '$3 >= 1000 && $3 < 65534 {print $1}' | head -1)
BACKUP_NAME="${PROJECT_USER}-vps-backup"
BACKUP_DIR="/backup/vps-config"
CRITICAL_PATHS=(
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
    "/etc/iptables"
    "/etc/ufw"
    "/var/spool/cron"
    "/etc/crontab"
    "/etc/cron.d"
    "/etc/cron.daily"
    "/etc/cron.weekly"
    "/etc/cron.monthly"
    "/etc/cron.hourly"
    "/etc/hosts"
    "/etc/resolv.conf"
    "/etc/passwd"
    "/etc/group"
    "/etc/shadow"
    "/etc/sudoers"
    "/etc/sudoers.d"
)

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root or with sudo"
        log_info "Current user: $(whoami), EUID: $EUID"
        exit 1
    fi
}

backup_vps() {
    log_info "Starting VPS backup..."
    log_info "Backup started at: $(date)"
    log_info "Backup initiated by user: $(whoami)"
    log_info "System: $(hostname) - $(uname -a)"
    
    # Create backup directory with timestamp
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_PATH="$BACKUP_DIR/$TIMESTAMP"
    mkdir -p "$BACKUP_PATH"
    log_info "Created backup directory: $BACKUP_PATH"
    
    # Create system info
    cat > "$BACKUP_PATH/system-info.txt" << EOF
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

Kubernetes Status:
$(kubectl version --short 2>/dev/null || echo "Kubernetes not available")

WireGuard Status:
$(wg show 2>/dev/null || echo "WireGuard not available")

SSH Status:
$(systemctl is-active ssh 2>/dev/null || echo "SSH not available")
EOF

    # Backup critical paths
    log_info "Starting backup of critical paths..."
    BACKED_UP_COUNT=0
    SKIPPED_COUNT=0
    TOTAL_SIZE=0
    
    for path in "${CRITICAL_PATHS[@]}"; do
        if [ -e "$path" ]; then
            # Get size before backup
            if [ -d "$path" ]; then
                SIZE=$(du -sh "$path" 2>/dev/null | cut -f1)
                TYPE="directory"
            else
                SIZE=$(du -sh "$path" 2>/dev/null | cut -f1)
                TYPE="file"
            fi
            
            log_info "Backing up $TYPE: $path (size: $SIZE)"
            
            # Create destination directory
            DEST_DIR="$BACKUP_PATH$(dirname "$path")"
            mkdir -p "$DEST_DIR"
            
            # Copy with preserve attributes
            if cp -a "$path" "$DEST_DIR/" 2>/dev/null; then
                log_success "✓ Successfully backed up: $path"
                BACKED_UP_COUNT=$((BACKED_UP_COUNT + 1))
            else
                log_error "✗ Failed to backup: $path"
            fi
        else
            log_warning "✗ Path does not exist: $path"
            SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
        fi
    done
    
    log_info "Backup summary: $BACKED_UP_COUNT items backed up, $SKIPPED_COUNT items skipped"
    
    # Create compressed archive
    log_info "Creating compressed archive..."
    cd "$BACKUP_DIR"
    
    # Get uncompressed size
    UNCOMPRESSED_SIZE=$(du -sh "$TIMESTAMP" | cut -f1)
    log_info "Uncompressed backup size: $UNCOMPRESSED_SIZE"
    
    if tar -czf "${TIMESTAMP}.tar.gz" "$TIMESTAMP" 2>/dev/null; then
        log_success "✓ Archive created successfully"
    else
        log_error "✗ Failed to create archive"
        exit 1
    fi
    
    # Get compressed size and show compression ratio
    COMPRESSED_SIZE=$(du -h "${TIMESTAMP}.tar.gz" | cut -f1)
    log_info "Compressed backup size: $COMPRESSED_SIZE"
    
    # Clean up uncompressed backup
    rm -rf "$TIMESTAMP"
    log_info "Cleaned up temporary files"
    
    log_success "VPS backup completed: $BACKUP_DIR/${TIMESTAMP}.tar.gz"
    log_info "Backup finished at: $(date)"
}

restore_vps() {
    log_info "Starting VPS restore..."
    
    # Find latest backup
    LATEST_BACKUP=$(ls -t "$BACKUP_DIR"/*.tar.gz 2>/dev/null | head -1)
    
    if [ -z "$LATEST_BACKUP" ]; then
        log_error "No backup files found in $BACKUP_DIR"
        exit 1
    fi
    
    log_info "Restoring from: $LATEST_BACKUP"
    
    # Extract backup
    TEMP_DIR="/tmp/vps-restore-$$"
    mkdir -p "$TEMP_DIR"
    tar -xzf "$LATEST_BACKUP" -C "$TEMP_DIR"
    
    # Find the extracted directory
    EXTRACTED_DIR=$(ls "$TEMP_DIR" | head -1)
    RESTORE_PATH="$TEMP_DIR/$EXTRACTED_DIR"
    
    # Restore critical paths
    for path in "${CRITICAL_PATHS[@]}"; do
        BACKUP_PATH="$RESTORE_PATH$path"
        if [ -e "$BACKUP_PATH" ]; then
            log_info "Restoring: $path"
            # Create destination directory if needed
            mkdir -p "$(dirname "$path")"
            # Copy with preserve attributes
            cp -a "$BACKUP_PATH" "$(dirname "$path")/"
        fi
    done
    
    # Restart services
    log_info "Restarting services..."
    systemctl daemon-reload
    systemctl restart ssh
    systemctl restart k3s 2>/dev/null || true
    systemctl restart wireguard 2>/dev/null || true
    
    # Clean up
    rm -rf "$TEMP_DIR"
    
    log_success "VPS restore completed successfully!"
}

list_backups() {
    log_info "Available backups:"
    if [ -d "$BACKUP_DIR" ]; then
        ls -lh "$BACKUP_DIR"/*.tar.gz 2>/dev/null || echo "No backup files found"
    else
        echo "Backup directory does not exist"
    fi
}

cleanup_old_backups() {
    log_info "Cleaning up old backups (keeping last 5)..."
    if [ -d "$BACKUP_DIR" ]; then
        # Keep only the 5 most recent backups
        ls -t "$BACKUP_DIR"/*.tar.gz 2>/dev/null | tail -n +6 | xargs rm -f
        log_success "Cleanup completed"
    else
        log_warning "Backup directory does not exist"
    fi
}

# Main script
case "$1" in
    "backup")
        check_root
        backup_vps
        ;;
    "restore")
        check_root
        restore_vps
        ;;
    "list")
        list_backups
        ;;
    "cleanup")
        check_root
        cleanup_old_backups
        ;;
    *)
        echo "Simple VPS Backup and Restore Script"
        echo "Usage: $0 {backup|restore|list|cleanup}"
        echo ""
        echo "Commands:"
        echo "  backup   - Create a complete backup of critical VPS configs"
        echo "  restore  - Restore the VPS from the latest backup"
        echo "  list     - List available backups"
        echo "  cleanup  - Clean up old backups (keep last 5)"
        echo ""
        echo "Examples:"
        echo "  $0 backup    # Create backup"
        echo "  $0 restore   # Restore from backup"
        echo "  $0 list      # Show available backups"
        exit 1
        ;;
esac 