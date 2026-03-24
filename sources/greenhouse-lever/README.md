# Greenhouse & Lever fetcher

API-based (no Selenium). Inspired by [MarcusKyung/greenhouse.io-scraper](https://github.com/MarcusKyung/greenhouse.io-scraper).

## Example companies

**Greenhouse** (boards-api):
- figma, stripe, kallesgroup, energysolutions, arcadiacareers, airship

**Lever** (api.lever.co):
- pigment, coforma, lever, theathletic, vrchat, fanatics, nielsen

## Usage

```bash
python fetch.py --source greenhouse --company figma
python fetch.py --source lever --company pigment --limit 20
```
