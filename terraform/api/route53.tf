data "aws_route53_zone" "zone" {
  name         = "maths22.com"
  private_zone = false
}

resource "aws_route53_record" "domain" {
  name = "pace.maths22.com"
  type = "A"
  zone_id = data.aws_route53_zone.zone.zone_id

  alias {
    name = aws_cloudfront_distribution.distribution.domain_name
    zone_id = aws_cloudfront_distribution.distribution.hosted_zone_id
    evaluate_target_health = false
  }
}