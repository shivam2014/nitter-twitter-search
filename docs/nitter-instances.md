# Nitter Mirror Instances

This file contains known working Nitter mirror instances. These are fetched from https://status.d420.de/api/v1/instances when available.

## How to Fetch Fresh Mirrors

The skill automatically fetches from:
```
https://status.d420.de/api/v1/instances
```

If that endpoint is unavailable, it will search for alternative mirrors.

## Known Mirrors (Verified)

### Primary Mirrors
- `https://nitter.net` - Original/main instance
- `https://nitter.pussthecat.org` - Popular alternative
- `https://nitter.fdn.fr` - FDN-hosted instance
- `https://nitter.hyperrealistic.dev` - Hyperrealistic instance

### Secondary Mirrors
- `https://nitter.projectsegfau.lt` - Project Segfau.lt
- `https://nitter.dread.so` - Dread.so instance
- `https://nitter.totallynotanactualwebservice.com` - TotallyNotAnActualWebService
- `https://nitter.josecloud.xyz` - JoseCloud instance

### Additional Mirrors (Unverified Status)
- `https://nitter.bloat.tech`
- `https://nitter.bus-hit.me`
- `https://nitter.datenschutz.xyz`
- `https://nitter.ducks.party`
- `https://nitter.fisketroll.se`
- `https://nitter.ikaros.dev`
- `https://nitter.itsnotabackdoor.com`
- `https://nitter.libredd.it`
- `https://nitter.mastodon.cloud`
- `https://nitter.privacyfucking.rocks`
- `https://nitter.rootzclub.com`
- `https://nitter.rouge-coeur.com`
- `https://nitter.saidit.net`
- `https://nitter.sopuli.xyz`
- `https://nitter.voxh.com`
- `https://nitter.zapashcanon.fr`

## Mirror Health Check

To check mirror status in real-time:
```
https://status.d420.de/
```

Or via API:
```
https://status.d420.de/api/v1/instances
```

## Notes

- Nitter instances can go offline frequently due to X/Twitter blocking
- The skill automatically tries multiple mirrors when one fails
- If all mirrors are down, it will fall back to camoufox-cli browser automation
- Some mirrors may be region-locked or blocked in certain countries

## Adding New Mirrors

If you know of a working Nitter mirror that's not in this list:
1. Test it manually: `curl -I https://<mirror-url>`
2. If it responds with 200 OK, it's working
3. Add it to this list with verification timestamp
4. Consider adding to the skill's internal mirror list
