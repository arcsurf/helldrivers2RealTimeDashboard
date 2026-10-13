"""Cliente mínimo para la API comunitaria de Helldivers 2 (https://helldivers-2.github.io/api)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

import requests

BASE_URL = "https://api.helldivers2.dev"
HEADERS = {
    # La API exige identificar al cliente; cámbialos si publicas la app.
    "X-Super-Client": "hd2-dashboard-python",
    "X-Super-Contact": "hd2-dashboard-local",
    "Accept-Language": "es-ES",
}


@dataclass
class Campaign:
    planet: str
    sector: str
    faction: str          # facción enemiga contra la que se lucha
    players: int
    liberation: float     # 0-100
    is_defense: bool
    biome: str
    ends: datetime | None = None


@dataclass
class Snapshot:
    fetched_at: datetime
    players: int
    success_rate: float
    impact: float
    missions_won: int
    missions_lost: int
    deaths: int
    kills: dict[str, int]
    campaigns: list[Campaign] = field(default_factory=list)
    major_orders: list[dict] = field(default_factory=list)


def _get(session: requests.Session, path: str):
    r = session.get(BASE_URL + path, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.json()


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _campaign(raw: dict) -> Campaign:
    p = raw["planet"]
    event = p.get("event")
    if event:
        faction, health, max_health = event["faction"], event["health"], event["maxHealth"]
    else:
        faction, health, max_health = p["currentOwner"], p["health"], p["maxHealth"]
    liberation = (1 - health / max_health) * 100 if max_health else 0.0
    return Campaign(
        planet=p["name"].title(),
        sector=p.get("sector", ""),
        faction=faction,
        players=p["statistics"]["playerCount"],
        liberation=max(0.0, min(100.0, liberation)),
        is_defense=bool(event),
        biome=(p.get("biome") or {}).get("name", ""),
        ends=_parse_time(event.get("endTime")) if event else None,
    )


def fetch_snapshot(session: requests.Session | None = None) -> Snapshot:
    """Descarga el estado actual de la guerra (3 peticiones, dentro del rate limit de 5/10s)."""
    session = session or requests.Session()
    war = _get(session, "/api/v1/war")
    campaigns = _get(session, "/api/v1/campaigns")
    assignments = _get(session, "/api/v1/assignments")

    s = war["statistics"]
    return Snapshot(
        fetched_at=datetime.now(timezone.utc),
        players=s["playerCount"],
        success_rate=s["missionSuccessRate"],
        impact=war.get("impactMultiplier", 0.0),
        missions_won=s["missionsWon"],
        missions_lost=s["missionsLost"],
        deaths=s["deaths"],
        kills={
            "Terminids": s["terminidKills"],
            "Automaton": s["automatonKills"],
            "Illuminate": s["illuminateKills"],
        },
        campaigns=sorted((_campaign(c) for c in campaigns), key=lambda c: c.players, reverse=True),
        major_orders=assignments,
    )
