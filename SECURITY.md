# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in openguard, please report it privately to the maintainers before disclosing it publicly.

- Email: security@learnhelp.cc (or contact a maintainer via GitHub)
- Do **not** open a public issue with sensitive details.

We will respond within 5 business days and work to address the issue promptly.

## Supported Versions

Only the latest stable release of openguard is supported for security updates.

## Security Best Practices

- **Bot Tokens:** Never share your bot token or commit it to version control.
- **Updates:** Keep dependencies and the openguard codebase up-to-date to avoid known vulnerabilities.
- **Permissions:** Run the bot with the minimum Discord permissions necessary.
- **Configuration:** Ensure your `config.yaml` is stored securely and never posted publicly.
- **Auditing:** Regularly review moderation logs for suspicious activity.

## Dependencies

openguard relies on Python packages as defined in `requirements.txt`. Please review their security advisories as part of your deployment process.

## Disclosure Policy

If a critical vulnerability is discovered, an advisory will be posted in the GitHub repository and a patch released as soon as possible.
