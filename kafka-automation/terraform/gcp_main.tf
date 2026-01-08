# File: kafka-automation/terraform/gcp_main.tf
# File này bản rút gọn của main.tf phục vụ mục đích tham khảo nhanh

provider "google" {
  project = "YOUR_PROJECT_ID"
  region  = "asia-southeast1"
}

resource "google_compute_instance" "kafka_nodes" {
  count        = 3
  name         = "kafka-node-${count.index + 1}"
  machine_type = "e2-standard-4"
  zone         = "asia-southeast1-a"

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2404-lts-amd64"
      size  = 50
      type  = "pd-ssd"
    }
  }

  network_interface {
    network = "default"
    access_config {}
  }

  metadata = {
    ssh-keys = "tienthanhtk115:${file("~/.ssh/bigdata_key.pub")}"
  }

  tags = ["kafka-cluster"]
}
