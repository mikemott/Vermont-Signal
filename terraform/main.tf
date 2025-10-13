terraform {
  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.45"
    }
  }
  required_version = ">= 1.0"
}

variable "hcloud_token" {
  description = "Hetzner Cloud API Token"
  type        = string
  sensitive   = true
}

variable "ssh_public_key" {
  description = "SSH public key for server access"
  type        = string
}

variable "domain_name" {
  description = "Domain name for the application (optional)"
  type        = string
  default     = ""
}

variable "server_name" {
  description = "Name of the server"
  type        = string
  default     = "vermont-signal"
}

provider "hcloud" {
  token = var.hcloud_token
}

# SSH Key
resource "hcloud_ssh_key" "default" {
  name       = "${var.server_name}-key"
  public_key = var.ssh_public_key
}

# Firewall
resource "hcloud_firewall" "web" {
  name = "${var.server_name}-firewall"

  # SSH
  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "22"
    source_ips = [
      "0.0.0.0/0",
      "::/0"
    ]
  }

  # HTTP
  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "80"
    source_ips = [
      "0.0.0.0/0",
      "::/0"
    ]
  }

  # HTTPS
  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "443"
    source_ips = [
      "0.0.0.0/0",
      "::/0"
    ]
  }

  # API Port (for testing without domain)
  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "8000"
    source_ips = [
      "0.0.0.0/0",
      "::/0"
    ]
  }
}

# Server
resource "hcloud_server" "main" {
  name        = var.server_name
  server_type = "cpx31"  # 4 vCPUs, 8GB RAM, 160GB SSD - $10.50/month
  image       = "ubuntu-24.04"
  location    = "nbg1"  # Nuremberg, Germany (or use "hel1" for Helsinki, "fsn1" for Falkenstein)

  ssh_keys = [hcloud_ssh_key.default.id]

  firewall_ids = [hcloud_firewall.web.id]

  user_data = file("${path.module}/cloud-init.yaml")

  labels = {
    app = "vermont-signal"
  }

  public_net {
    ipv4_enabled = true
    ipv6_enabled = true
  }
}

# Outputs
output "server_ip" {
  value       = hcloud_server.main.ipv4_address
  description = "Public IPv4 address of the server"
}

output "server_ipv6" {
  value       = hcloud_server.main.ipv6_address
  description = "Public IPv6 address of the server"
}

output "server_status" {
  value       = hcloud_server.main.status
  description = "Server status"
}

output "ssh_command" {
  value       = "ssh root@${hcloud_server.main.ipv4_address}"
  description = "SSH command to access the server"
}

output "api_url" {
  value       = var.domain_name != "" ? "https://${var.domain_name}/api" : "http://${hcloud_server.main.ipv4_address}:8000/api"
  description = "API URL"
}
