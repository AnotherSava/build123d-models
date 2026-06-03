# MakerWorld API Research (Feb 2026)

## No Public API
MakerWorld has no official public API for model publishing. Forum requests since Jan 2024 with no Bambu Lab response.

## Known Internal Details
- Auth shared with api.bambulab.com via Bearer tokens (same Bambu Lab account)
- Microservice architecture: `design-user-service` naming pattern
- BambuStudio uploads via closed-source network plugin (libbambu_networking)

## Community Projects (Printer-Only)
- OpenBambuAPI (Doridian): https://github.com/Doridian/OpenBambuAPI — printer communication, not MakerWorld
- bambu-lab-cloud-api (PyPI): printer cloud API, MQTT, FTP — not MakerWorld publishing

## Approach Options
1. **Intercept API calls**: Use browser DevTools during manual model creation to capture endpoints, then replicate in Python. More robust.
2. **Playwright automation**: Fill web forms programmatically. Already have Playwright working with MakerWorld (headless=False to bypass Cloudflare).

## Recommended Next Step
Option 2 (Playwright) is fastest to implement since we already have the infrastructure. Option 1 is worth exploring for a more stable long-term solution.

## Sources
- Forum: https://forum.bambulab.com/t/public-api-for-makerworld/52699
- Forum: https://forum.bambulab.com/t/feature-request-makerworld-api-or-rss-feed-for-user-data/205669
- Wiki: https://wiki.bambulab.com/en/makerworld/tutorials/how-to-upload-models
