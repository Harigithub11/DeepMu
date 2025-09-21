# DNS Configuration for deepmu.tech

## Required DNS Records

Configure the following DNS records in your domain registrar's control panel:

### A Records (Point to your server IP)
```
A    deepmu.tech          →  YOUR_SERVER_IP
A    api.deepmu.tech      →  YOUR_SERVER_IP
A    admin.deepmu.tech    →  YOUR_SERVER_IP
A    docs.deepmu.tech     →  YOUR_SERVER_IP
```

### CNAME Records (Alternative if using subdomains)
```
CNAME api.deepmu.tech      →  deepmu.tech
CNAME admin.deepmu.tech    →  deepmu.tech
CNAME docs.deepmu.tech     →  deepmu.tech
```

### CAA Records (Certificate Authority Authorization)
```
CAA  deepmu.tech  0 issue "letsencrypt.org"
CAA  deepmu.tech  0 issuewild "letsencrypt.org"
```

### MX Records (Email - Optional)
```
MX   deepmu.tech  10 mail.deepmu.tech
```

### TXT Records (Domain Verification)
```
TXT  deepmu.tech  "v=spf1 include:_spf.google.com ~all"
TXT  _dmarc.deepmu.tech  "v=DMARC1; p=quarantine; rua=mailto:dmarc@deepmu.tech"
```

## DNS Propagation Check

After configuring DNS records, verify propagation:

```bash
# Check A records
dig deepmu.tech
dig api.deepmu.tech
dig admin.deepmu.tech

# Check from multiple locations
nslookup deepmu.tech 8.8.8.8
nslookup deepmu.tech 1.1.1.1

# Online tools
# https://www.whatsmydns.net/#A/deepmu.tech
# https://dnschecker.org/
```

## SSL Certificate Verification

Once DNS is propagated, verify SSL:

```bash
# Test SSL connectivity
openssl s_client -connect deepmu.tech:443 -servername deepmu.tech
curl -I https://api.deepmu.tech

# Check certificate details
echo | openssl s_client -connect deepmu.tech:443 2>/dev/null | openssl x509 -noout -dates
