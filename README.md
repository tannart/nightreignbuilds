# nightreignbuilds.fyi

Share and discover builds for *Elden Ring Nightreign*: pick a Nightfarer,
slot in relics and weapons, then save the build or grab a share link.

**Live:** https://nightreignbuilds.fyi

## Features

- **Builder.** Choose a Nightfarer and vessel, toggle Deep of Night (three or
  six relic slots), and fill each slot with a guaranteed relic, one of your
  saved relics, or a custom relic described on the spot. Relics that don't
  fit a slot's colour are hidden, and the server checks them too.
- **Save or share.** Saving lists a build under your name. A share link
  works without an account: it makes an unlisted build at a random URL such
  as `/b/ETrBueHi/`. Any build can be remixed.
- **Catalogue.** All 10 Nightfarers, 74 vessels with their slot colours,
  118 guaranteed relics, 387 weapons, and about 340 relic effects used as
  suggestions for custom relics. Relic and weapon icons are served by the
  site itself.
- **Live search** on the builds, relics and weapons pages.

## Stack

Django 6.1 on Python 3.13, PostgreSQL in production and SQLite locally.
Static files are served by WhiteNoise. Hosting is on [Railway](https://railway.com)
with DNS on Cloudflare. There is no frontend build step: plain CSS and a
couple of small scripts.

## Running locally

Dependencies are managed with [uv](https://docs.astral.sh/uv/).

```sh
uv sync
uv run python manage.py migrate
uv run python manage.py seed_game_data   # nightfarers, vessels, relics, weapons
uv run python manage.py createsuperuser  # optional, for /admin/
uv run python manage.py runserver
```

`seed_game_data` is safe to run repeatedly: it updates rows in place from
the files in `builds/data/`.

### Settings

Everything has a development default. Production sets these on Railway:

| Variable | Purpose |
|---|---|
| `DJANGO_SECRET_KEY` | Secret key (dev default is insecure) |
| `DJANGO_DEBUG` | `false` in production |
| `DATABASE_URL` | Postgres URL; SQLite when unset |
| `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS` | Comma-separated overrides |
| `DJANGO_CANONICAL_HOST` | `www.` on this host redirects to it |

## Tests and tooling

```sh
uv run pytest
uv run pre-commit install   # black, ruff and mypy on every commit
```

Tests use pytest-django with factory_boy for test data.

## Project layout

```
builds/
  models.py           Nightfarer, Vessel, Relic, RelicEffect, Weapon, Build
  forms.py            BuilderForm and the per-slot SlotForm
  views.py            builder, build pages, relic and weapon lists
  live_search.py      LiveSearchMixin for list views
  templatetags/       {% livesearch %} search form component
  data/               game data seeded by seed_game_data
config/               settings, URLs, www redirect middleware
templates/            base layout and shared components
static/               CSS, JS, relic and weapon icons
.railway/railway.py   Railway service config (infrastructure as code)
```

### Live search component

Any list view can get search-as-you-type:

```python
class ThingListView(LiveSearchMixin, generic.ListView[Thing]):
    live_results_template = "builds/_thing_results.html"
    live_noun = "thing"
```

```django
{% load live_search %}
{% livesearch placeholder="Search things" keep="some_filter" %}{% endlivesearch %}
{% include "components/live_results.html" %}
```

## Deployment

Pushes to `master` deploy to Railway. Before each release Railway runs
`migrate` and `seed_game_data`, so changes to `builds/data/` reach
production automatically. Service settings live in `.railway/railway.py`.
Preview changes with `uv run railway config plan` and apply them with
`uv run railway config apply`.

## Data and credits

Vessel, relic and weapon data and icons come from the
[Elden Ring Nightreign wiki](https://eldenring.wiki.gg/) (text under
CC BY-SA). The random relic effect list comes from
[Game8](https://game8.co/games/Elden-Ring-Nightreign). Game assets are
© FromSoftware / Bandai Namco. This is a fan project and is not
affiliated with either company.
