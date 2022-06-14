terraform {
  backend "s3" {
    bucket = "maths22-remote-tfstate"
    region = "us-west-2"
    key    = "us-east-2/pace-bus-tracker/terraform/api.tfstate"
  }
}