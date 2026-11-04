"""Typed subset of football-data.org v4; unknown provider fields are ignored."""

from datetime import date, datetime

from pydantic import BaseModel, Field


class ProviderTeam(BaseModel):
    id: int | None
    name: str | None


class ProviderSeason(BaseModel):
    id: int
    start_date: date = Field(alias="startDate")


class FullTimeScore(BaseModel):
    home: int | None
    away: int | None


class Score(BaseModel):
    full_time: FullTimeScore = Field(alias="fullTime")


class ProviderMatch(BaseModel):
    id: int
    season: ProviderSeason
    home_team: ProviderTeam = Field(alias="homeTeam")
    away_team: ProviderTeam = Field(alias="awayTeam")
    score: Score
    utc_date: datetime = Field(alias="utcDate")
    status: str


class ProviderCompetition(BaseModel):
    name: str


class MatchesResponse(BaseModel):
    competition: ProviderCompetition
    matches: list[ProviderMatch]


class StandingRow(BaseModel):
    team: ProviderTeam
    position: int = Field(ge=1)
    points: int
    played_games: int = Field(alias="playedGames", ge=0)


class StandingGroup(BaseModel):
    type: str
    stage: str
    group: str | None = None
    table: list[StandingRow]


class StandingsResponse(BaseModel):
    season: ProviderSeason
    standings: list[StandingGroup]
