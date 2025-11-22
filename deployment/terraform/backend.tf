terraform {
  backend "gcs" {
    bucket = "gradr-421618-terraform-state"
    prefix = "gradr-agent/prod"
  }
}
