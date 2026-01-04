# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in vision-connector, please report it responsibly:

1. **Do NOT** open a public GitHub issue for security vulnerabilities
2. Email the maintainer directly at rogermsc@gmail.com
3. Include a detailed description of the vulnerability
4. Provide steps to reproduce if possible

We will acknowledge receipt within 48 hours and provide a more detailed response within 7 days.

## Security Best Practices

When using vision-connector in production:

### MQTT Connections

- Always use TLS encryption (`use_tls=True`)
- Use strong authentication credentials
- Avoid `tls_insecure=True` in production

```python
mqtt = MQTTOutput(
    "broker.example.com:8883",
    topic="plant/readings",
    use_tls=True,
    tls_ca_certs="/path/to/ca.crt",
    username="user",
    password="strong_password"
)
```

### Webhook Endpoints

- Always use HTTPS endpoints in production
- Keep `verify_ssl=True` (default)
- Use API keys or authentication

```python
webhook = WebhookOutput(
    "https://api.example.com/readings",
    api_key="your_api_key",
    verify_ssl=True  # default
)
```

### File Paths

- Validate and sanitize user-provided file paths
- Use absolute paths when possible
- Restrict output directories in production

### Configuration Files

- Do not commit configuration files with credentials
- Use environment variables for sensitive values
- Set appropriate file permissions (600) on config files
