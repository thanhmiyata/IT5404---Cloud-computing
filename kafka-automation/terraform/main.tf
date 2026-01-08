# File: kafka-automation/terraform/main.tf

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = "big-keyword-482311-r5" # Thay bằng Project ID của bạn
  region  = "asia-southeast1" # Singapore
}

# Tạo 3 máy ảo (VM Instances)
resource "google_compute_instance" "kafka_nodes" {
  count        = 3
  name         = "kafka-node-${count.index + 1}"
  machine_type = "e2-standard-4" # 4 vCPU, 16GB Memory
  zone         = "asia-southeast1-a"

  tags = ["kafka-cluster"]

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2404-lts-amd64" # Ubuntu 24.04 LTS
      size  = 50                                     # 50GB
      type  = "pd-ssd"                               # SSD
    }
  }

  network_interface {
    network = "default"
    access_config {
      # Cấp IP Public (Ephemeral IP)
    }
  }

  # Tự động gán SSH key để Ansible có thể kết nối
  metadata = {
    ssh-keys = "tienthanhtk115:${file("~/.ssh/bigdata_key.pub")}"
  }
}

# Cấu hình Firewall để mở port cho Kafka (9092, 9093) và SSH (22)
resource "google_compute_firewall" "kafka_rules" {
  name    = "allow-kafka-traffic"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["22", "9092", "9093"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["kafka-cluster"]
}

# Trả về danh sách IP Public của các máy sau khi tạo xong
output "cluster_public_ips" {
  value = google_compute_instance.kafka_nodes[*].network_interface[0].access_config[0].nat_ip
}
