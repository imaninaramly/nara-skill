# nara-skill

Skills for Claude Code.

## pinterest

Study Pinterest pins as design references (palette, layout, typography, recurring elements) for personal inspiration.

| Source | Works? |
|---|---|
| Public pin links (`pinterest.com/pin/...`, `pin.it/...`) | Yes. Picture, title, description and palette, no login needed. |
| Screenshots you send | Yes. Read directly. |
| Your own boards, secret ones too, and search | Yes, through the **official Pinterest API** with your own token in `PINTEREST_TOKEN`. Whatever the API refuses stays refused. |
| Search or boards without a token, logging in, cookies, Pinterest's internal endpoints | No, by design. |

Pins are other people's work: they are a style reference only. The skill does not cut elements out of pins or reuse a pin's picture in your own product or video.

### Install

Copy the folder `skills/pinterest` to `.claude/skills/pinterest` (one project) or `~/.claude/skills/pinterest` (all projects).

The sandbox needs to reach `www.pinterest.com`, `i.pinimg.com`, `pin.it` (and `api.pinterest.com` for the official API). The helper needs `curl` and Pillow.

### Use

```
python3 scripts/pin_fetch.py OUTDIR <pin link> [<pin link> ...]
python3 scripts/pin_fetch.py OUTDIR --file links.txt
export PINTEREST_TOKEN=...                          # official API v5 token, set in the environment, never in chat
python3 scripts/pin_fetch.py OUTDIR --api-boards
python3 scripts/pin_fetch.py OUTDIR --api-board BOARD_ID
python3 scripts/pin_fetch.py OUTDIR --api-search "query"
```

It writes `pin_XX.jpg`, `pins.json` and a contact sheet `sheet.jpg` into `OUTDIR`.
