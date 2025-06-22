# Server Setup Guide (Step-by-Step for Operator)

## 1. SSH Key Setup
1. **Check if SSH keys exist locally:**
   ```bash
   ls -la ~/.ssh/rop01_key*
   ```
   If not, generate them:
   ```bash
   ssh-keygen -t ed25519 -f ~/.ssh/rop01_key
   ```

2. **Remove old SSH host keys (if reconnecting):**
   ```bash
   ssh-keygen -R 217.154.24.75
   ssh-keygen -R 10.0.0.1
   ```

3. **Copy your public key to the server for passwordless SSH:**
   ```bash
   ssh-copy-id -i ~/.ssh/rop01_key.pub root@217.154.24.75
   ```
   Test passwordless SSH:
   ```bash
   ssh -i ~/.ssh/rop01_key root@217.154.24.75 "echo 'Passwordless SSH works'"
   ```

## 2. WireGuard Installation on Server
1. **Install WireGuard:**
   ```bash
   ssh -i ~/.ssh/rop01_key root@217.154.24.75 "apt update && apt install -y wireguard"
   ```

## 3. Generate WireGuard Keys on Server
1. **Generate keys:**
   ```bash
   ssh -i ~/.ssh/rop01_key root@217.154.24.75 "mkdir -p /etc/wireguard && cd /etc/wireguard && wg genkey | tee privatekey | wg pubkey > publickey && chmod 600 privatekey && chmod 644 publickey"
   ```
2. **Get the server's public key:**
   ```bash
   ssh -i ~/.ssh/rop01_key root@217.154.24.75 "cat /etc/wireguard/publickey"
   ```
3. **Get the server's private key (for config):**
   ```bash
   ssh -i ~/.ssh/rop01_key root@217.154.24.75 "cat /etc/wireguard/privatekey"
   ```

## 4. Get Local (Mac) WireGuard Keys
1. **Get your local public key:**
   ```bash
   sudo cat /etc/wireguard/client_public.key
   ```
2. **Get your local private key:**
   ```bash
   sudo cat /etc/wireguard/client_private.key
   ```

## 5. Create WireGuard Configs
1. **Server config (`server_wg0.conf`):**
   ```ini
   [Interface]
   Address = 10.0.0.1/24
   SaveConfig = false
   ListenPort = 51820
   PrivateKey = <server_private_key>

   [Peer]
   PublicKey = <client_public_key>
   AllowedIPs = 10.0.0.2/32
   ```
2. **Client config (`client_wg0.conf`):**
   ```ini
   [Interface]
   PrivateKey = <client_private_key>
   Address = 10.0.0.2/24
   DNS = 1.1.1.1

   [Peer]
   PublicKey = <server_public_key>
   Endpoint = 217.154.24.75:51820
   AllowedIPs = 10.0.0.0/24
   PersistentKeepalive = 25
   ```

## 6. Deploy Configs
1. **Copy server config to server:**
   ```bash
   scp -i ~/.ssh/rop01_key server_wg0.conf root@217.154.24.75:/etc/wireguard/wg0.conf
   ssh -i ~/.ssh/rop01_key root@217.154.24.75 "chmod 600 /etc/wireguard/wg0.conf"
   ```
2. **Copy client config locally:**
   ```bash
   sudo cp client_wg0.conf /etc/wireguard/wg0.conf
   sudo chmod 600 /etc/wireguard/wg0.conf
   ```

## 7. Restart WireGuard Interfaces
1. **On the server:**
   ```bash
   ssh -i ~/.ssh/rop01_key root@217.154.24.75 "systemctl restart wg-quick@wg0"
   ```
2. **On the Mac:**
   ```bash
   sudo wg-quick down wg0 || true && sudo wg-quick up wg0
   ```

## 8. Test Connectivity
1. **Ping the server from your Mac:**
   ```bash
   ping -c 3 10.0.0.1
   ```
   You should see successful replies.

---

**Repeat these steps exactly for a clean, working WireGuard and SSH setup.**

## Notes
- Ensure proper permissions are set for SSH and WireGuard configurations
- Verify connectivity after WireGuard restart
- Check logs if issues arise during setup