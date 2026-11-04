from sqlalchemy import delete

from backend.db import Competition, Match, Season, Standing, SyncLog, Team
from pitchsight.data.provider import FootballData, ProviderError


def seed_demo(factory):
    with factory.begin() as session:
        for code, name in [("PL", "Premier League"), ("CL", "Champions League")]:
            cid = f"demo-{code}"
            session.merge(Competition(id=cid, name=name, provenance="DEMO DATA"))
            session.flush()
            session.merge(Season(id=f"{cid}-2025", competition_id=cid, year=2025))
        for i, name in enumerate(
            ["Northbridge FC", "Harbour Athletic", "Kingsfield United", "Riverside City"]
        ):
            session.merge(Team(id=f"demo-{i}", name=name, provenance="DEMO DATA"))
        session.flush()
        for i in range(8):
            cid = "demo-PL" if i % 2 == 0 else "demo-CL"
            session.merge(
                Match(
                    id=f"demo-{i}",
                    competition_id=cid,
                    season_id=f"{cid}-2025",
                    home_id=f"demo-{i % 4}",
                    away_id=f"demo-{(i + 1) % 4}",
                    kickoff=f"2025-09-{10 + i:02}T19:00:00Z",
                    status="FINISHED" if i < 5 else "SCHEDULED",
                    home_score=i % 3 if i < 5 else None,
                    away_score=(i + 1) % 2 if i < 5 else None,
                    provenance="DEMO DATA",
                )
            )
        session.add(
            SyncLog(
                mode="demo",
                status="completed",
                detail="8 fictional matches seeded idempotently; no real results",
            )
        )


def sync_matches(factory, codes=("PL", "CL"), client=None):
    owned = client is None
    client = client or FootballData()
    try:
        for code in codes:
            if code not in ("PL", "CL"):
                raise ProviderError("Only PL and CL are supported")
            data = client.get(f"competitions/{code}/matches")
            with factory.begin() as session:
                session.merge(
                    Competition(id=code, name=data["competition"]["name"], provenance="LIVE API")
                )
                session.flush()
                for row in data["matches"]:
                    season = row["season"]
                    sid = f"{code}-{season['id']}"
                    session.merge(
                        Season(id=sid, competition_id=code, year=int(season["startDate"][:4]))
                    )
                    for key in ("homeTeam", "awayTeam"):
                        team = row[key]
                        if team["id"] is None:
                            raise ProviderError(
                                "Unresolved team in provider data; sync rolled back"
                            )
                        session.merge(
                            Team(id=str(team["id"]), name=team["name"], provenance="LIVE API")
                        )
                    session.flush()
                    score = row["score"]["fullTime"]
                    session.merge(
                        Match(
                            id=str(row["id"]),
                            competition_id=code,
                            season_id=sid,
                            home_id=str(row["homeTeam"]["id"]),
                            away_id=str(row["awayTeam"]["id"]),
                            kickoff=row["utcDate"],
                            status=row["status"],
                            home_score=score["home"],
                            away_score=score["away"],
                            provenance="LIVE API",
                        )
                    )
            try:
                table = client.get(f"competitions/{code}/standings")
                with factory.begin() as session:
                    season = table["season"]
                    sid = f"{code}-{season['id']}"
                    session.merge(
                        Season(id=sid, competition_id=code, year=int(season["startDate"][:4]))
                    )
                    session.flush()
                    session.execute(delete(Standing).where(Standing.season_id == sid))
                    for group in table["standings"]:
                        if group["type"] != "TOTAL":
                            continue
                        for row in group["table"]:
                            team = row["team"]
                            session.merge(
                                Team(id=str(team["id"]), name=team["name"], provenance="LIVE API")
                            )
                            session.flush()
                            session.add(
                                Standing(
                                    season_id=sid,
                                    team_id=str(team["id"]),
                                    group_name=group.get("group") or "",
                                    stage=group["stage"],
                                    position=row["position"],
                                    points=row["points"],
                                    played=row["playedGames"],
                                    provenance="LIVE API",
                                )
                            )
            except ProviderError as exc:
                with factory.begin() as session:
                    session.add(
                        SyncLog(
                            mode="live",
                            status="partial",
                            detail=f"{code} matches synced; standings: {exc}",
                        )
                    )
                continue
            with factory.begin() as session:
                session.add(
                    SyncLog(
                        mode="live",
                        status="completed",
                        detail=f"{code} matches and standings synced",
                    )
                )
    except Exception as exc:
        with factory.begin() as session:
            session.add(
                SyncLog(
                    mode="live",
                    status="failed",
                    detail=str(exc)
                    if isinstance(exc, ProviderError)
                    else "Invalid provider payload; sync aborted",
                )
            )
        raise
    finally:
        if owned:
            client.close()
