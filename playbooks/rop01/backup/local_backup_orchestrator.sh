#!/bin/bash

# Local VPS Backup Orchestrator
# Runs from local machine, performs backup on remote VPS, downloads it locally, and cleans up

set -e

# Configuration - Update these for your environment
PROJECT_NAME="rop01"
VPS_IP="10.0.0.1"

# Derived configuration - automatically generated from above
VPS_USER="root"                      # Build VPS user from project name
SSH_KEY="~/.ssh/${PROJECT_NAME}_key"                 # Build SSH key path from project name
VPS_USERNAME="${PROJECT_NAME}_user"                  # Build username from project name (same as VPS_USER)
REMOTE_SCRIPT_PATH="/root/simple_backup_restore.sh"
LOCAL_BACKUP_DIR="./backup/backups"
REMOTE_BACKUP_DIR="/backup/vps-config"
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

check_config() {
    log_info "Checking configuration..."
    
    if [ ! -f "${SSH_KEY/#\~/$HOME}" ]; then
        log_error "SSH key not found: $SSH_KEY"
        exit 1
    fi
    
    # Test SSH connection
    if ! ssh -i "$SSH_KEY" -o ConnectTimeout=10 -o BatchMode=yes "$VPS_USER@$VPS_IP" "echo 'SSH connection OK'" &>/dev/null; then
        log_error "Cannot connect to VPS: $VPS_USER@$VPS_IP"
        log_error "Please check SSH key, IP address, and VPS status"
        exit 1
    fi
    
    log_success "Configuration OK"
}

ensure_remote_script() {
    log_info "Ensuring backup script exists on VPS..."
    
    # Check if script exists and is executable
    if ssh -i "$SSH_KEY" "$VPS_USER@$VPS_IP" "[ -f '$REMOTE_SCRIPT_PATH' ] && [ -x '$REMOTE_SCRIPT_PATH' ]"; then
        log_success "Remote backup script found and executable"
    else
        log_info "Copying backup script to VPS..."
        scp -i "$SSH_KEY" "./backup/simple_backup_restore.sh" "$VPS_USER@$VPS_IP:$REMOTE_SCRIPT_PATH"
        ssh -i "$SSH_KEY" "$VPS_USER@$VPS_IP" "chmod +x '$REMOTE_SCRIPT_PATH'"
        log_success "Backup script deployed to VPS"
    fi
}

backup_vps() {
    log_info "Starting remote VPS backup..."
    
    # Create local backup directory
    mkdir -p "$LOCAL_BACKUP_DIR"
    
    # Create timestamped log file name
    LOCAL_LOG_FILE="$LOCAL_BACKUP_DIR/backup_${PROJECT_NAME}_$(date '+%Y%m%d_%H%M%S').log"
    
    # Run backup on remote VPS and capture output locally
    log_info "Executing backup on VPS..."
    if ssh -i "$SSH_KEY" "$VPS_USER@$VPS_IP" "$REMOTE_SCRIPT_PATH backup" | tee "$LOCAL_LOG_FILE"; then
        log_success "Remote backup completed"
        log_info "Backup log saved to: $LOCAL_LOG_FILE"
    else
        log_error "Remote backup failed"
        exit 1
    fi
    
    # Get the latest backup filename
    log_info "Identifying latest backup file..."
    LATEST_BACKUP=$(ssh -i "$SSH_KEY" "$VPS_USER@$VPS_IP" "ls -t $REMOTE_BACKUP_DIR/*.tar.gz 2>/dev/null | head -1")
    
    if [ -z "$LATEST_BACKUP" ]; then
        log_error "No backup file found on VPS"
        exit 1
    fi
    
    BACKUP_FILENAME=$(basename "$LATEST_BACKUP")
    log_info "Latest backup: $BACKUP_FILENAME"
    
    # Download backup to local machine
    log_info "Downloading backup to local machine..."
    if scp -i "$SSH_KEY" "$VPS_USER@$VPS_IP:$LATEST_BACKUP" "$LOCAL_BACKUP_DIR/"; then
        log_success "Backup downloaded to: $LOCAL_BACKUP_DIR/$BACKUP_FILENAME"
    else
        log_error "Failed to download backup"
        exit 1
    fi
    
    # Get backup size for info
    LOCAL_BACKUP_SIZE=$(du -h "$LOCAL_BACKUP_DIR/$BACKUP_FILENAME" | cut -f1)
    log_info "Downloaded backup size: $LOCAL_BACKUP_SIZE"
    
    # Delete backup from VPS to save space
    log_info "Cleaning up remote backup file..."
    if ssh -i "$SSH_KEY" "$VPS_USER@$VPS_IP" "rm -f '$LATEST_BACKUP'"; then
        log_success "Remote backup file deleted"
    else
        log_warning "Failed to delete remote backup file"
    fi
    
    log_success "Backup operation completed successfully!"
    log_info "Local backup location: $LOCAL_BACKUP_DIR/$BACKUP_FILENAME"
}

restore_vps() {
    log_info "Starting VPS restore from local backup..."
    
    # Find latest local backup
    LATEST_LOCAL_BACKUP=$(ls -t "$LOCAL_BACKUP_DIR"/*.tar.gz 2>/dev/null | head -1)
    
    if [ -z "$LATEST_LOCAL_BACKUP" ]; then
        log_error "No local backup files found in $LOCAL_BACKUP_DIR"
        exit 1
    fi
    
    BACKUP_FILENAME=$(basename "$LATEST_LOCAL_BACKUP")
    log_info "Restoring from: $BACKUP_FILENAME"
    
    # Upload backup to VPS
    log_info "Uploading backup to VPS..."
    ssh -i "$SSH_KEY" "$VPS_USER@$VPS_IP" "mkdir -p '$REMOTE_BACKUP_DIR'"
    if scp -i "$SSH_KEY" "$LATEST_LOCAL_BACKUP" "$VPS_USER@$VPS_IP:$REMOTE_BACKUP_DIR/"; then
        log_success "Backup uploaded to VPS"
    else
        log_error "Failed to upload backup to VPS"
        exit 1
    fi
    
    # Run restore on VPS
    log_info "Executing restore on VPS..."
    if ssh -i "$SSH_KEY" "$VPS_USER@$VPS_IP" "$REMOTE_SCRIPT_PATH restore"; then
        log_success "Remote restore completed"
    else
        log_error "Remote restore failed"
        exit 1
    fi
    
    # Clean up uploaded backup
    log_info "Cleaning up uploaded backup file..."
    ssh -i "$SSH_KEY" "$VPS_USER@$VPS_IP" "rm -f '$REMOTE_BACKUP_DIR/$BACKUP_FILENAME'"
    
    log_success "Restore operation completed successfully!"
}

list_backups() {
    log_info "Available local backups:"
    if [ -d "$LOCAL_BACKUP_DIR" ] && [ "$(ls -A $LOCAL_BACKUP_DIR/*.tar.gz 2>/dev/null)" ]; then
        ls -lh "$LOCAL_BACKUP_DIR"/*.tar.gz 2>/dev/null | while read -r line; do
            echo "  $line"
        done
    else
        echo "  No local backup files found"
    fi
    
    log_info "Available local backup logs:"
    if [ -d "$LOCAL_BACKUP_DIR" ] && [ "$(ls -A $LOCAL_BACKUP_DIR/*.log 2>/dev/null)" ]; then
        ls -lh "$LOCAL_BACKUP_DIR"/*.log 2>/dev/null | while read -r line; do
            echo "  $line"
        done
    else
        echo "  No local log files found"
    fi
    
    log_info "Remote backups on VPS:"
    ssh -i "$SSH_KEY" "$VPS_USER@$VPS_IP" "ls -lh $REMOTE_BACKUP_DIR/*.tar.gz 2>/dev/null || echo '  No remote backup files found'"
}

cleanup_local() {
    log_info "Cleaning up old local backups and logs (keeping last 5 of each)..."
    if [ -d "$LOCAL_BACKUP_DIR" ]; then
        # Keep only the 5 most recent backups
        ls -t "$LOCAL_BACKUP_DIR"/*.tar.gz 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null || true
        # Keep only the 5 most recent log files
        ls -t "$LOCAL_BACKUP_DIR"/*.log 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null || true
        log_success "Local cleanup completed"
    else
        log_warning "Local backup directory does not exist"
    fi
}

show_config() {
    echo "Configuration (edit these only):"
    echo "  Project Name: $PROJECT_NAME"
    echo "  VPS IP: $VPS_IP"
    echo ""
    echo "Auto-Derived (no editing needed):"
    echo "  VPS User: $VPS_USER"
    echo "  SSH Key: $SSH_KEY"
    echo "  VPS Username: $VPS_USERNAME"
    echo "  Remote Script: $REMOTE_SCRIPT_PATH"
    echo "  Local Backup Dir: $LOCAL_BACKUP_DIR"
    echo "  Remote Backup Dir: $REMOTE_BACKUP_DIR"
    echo ""
    echo "Requirements:"
    echo "  - VPS user ($VPS_USER) must have sudo privileges (passwordless recommended)"
    echo "  - Backup script runs with 'sudo' for system file access"
}

# Main script
case "$1" in
    "backup")
        check_config
        ensure_remote_script
        backup_vps
        ;;
    "restore")
        check_config
        ensure_remote_script
        restore_vps
        ;;
    "list")
        check_config
        list_backups
        ;;
    "cleanup")
        cleanup_local
        ;;
    "config")
        show_config
        ;;
    *)
        echo "Local VPS Backup Orchestrator"
        echo "Usage: $0 {backup|restore|list|cleanup|config}"
        echo ""
        echo "Commands:"
        echo "  backup   - Create backup on VPS and download it locally"
        echo "  restore  - Upload local backup to VPS and restore it"
        echo "  list     - List available local and remote backups"
        echo "  cleanup  - Clean up old local backups (keep last 5)"
        echo "  config   - Show current configuration"
        echo ""
        echo "Examples:"
        echo "  $0 backup    # Backup VPS and download locally"
        echo "  $0 restore   # Restore VPS from local backup"
        echo "  $0 list      # Show available backups"
        echo ""
        echo "Configuration:"
        echo "  Edit script variables at the top to match your environment"
        exit 1
        ;;
esac
