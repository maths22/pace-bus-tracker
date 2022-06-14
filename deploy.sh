#!/usr/bin/env bash

export AWS_REGION=us-east-2
aws s3 sync ./wwwroot s3://pace-bus-history-tracker
aws cloudfront create-invalidation --distribution-id E29LO46ZLDL8ZS --paths "/*"