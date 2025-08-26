# MMA Module

Placeholder documentation for the upcoming MMA integration.

## Pages

- `GET /mma/` – dashboard with upcoming events, results, rankings, fighters, and news.

## API

The module currently exposes a limited JSON API:

- `GET /api/mma/events/` – list events (use `upcoming=1` to show future events).
- `GET /api/mma/events/<slug>/` – event detail.
- `GET /api/mma/news/` – list news items.
- `GET /api/mma/news/<slug>/` – news detail.

All timestamps are returned in the `Europe/Prague` timezone.

## Widgets

Two homepage widgets are available via the PH0ENIX picker:

- **MMA Upcoming** – shows the next scheduled events
- **MMA Results** – lists recent fight cards
