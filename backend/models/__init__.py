import enum
import uuid

from sqlalchemy import Column, Index, Integer, String, Boolean, Date, ForeignKey, DateTime, Float, UniqueConstraint, CheckConstraint, JSON, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


# --- Enums ---

class NotificationType(str, enum.Enum):
    injury_alert = "injury_alert"
    deadline_reminder = "deadline_reminder"

class NotificationStatus(str, enum.Enum):
    sent = "sent"
    failed = "failed"

class EntitlementStatus(str, enum.Enum):
    active = "active"
    revoked = "revoked"
    expired = "expired"

class EntitlementSource(str, enum.Enum):
    stripe = "stripe"
    apple_iap = "apple_iap"
    google_play = "google_play"

class Team(Base):
    __tablename__ = "teams"
    id = Column(Integer, primary_key=True, index=True)
    nba_team_id = Column(Integer, unique=True, nullable=False)
    abbreviation = Column(String(3), nullable=False)
    full_name = Column(String, nullable=False)

    # Record
    wins = Column(Integer, nullable=True)
    losses = Column(Integer, nullable=True)

    # Tempo & Defense
    pace = Column(Float, nullable=True)
    def_rating = Column(Float, nullable=True)

    # Opponent stats (what they allow - key for Fantasy prediction)
    opp_ppg = Column(Float, nullable=True)
    opp_rpg = Column(Float, nullable=True)
    opp_apg = Column(Float, nullable=True)
    opp_efg_pct = Column(Float, nullable=True)
    opp_tov = Column(Float, nullable=True)
    opp_stl = Column(Float, nullable=True)
    opp_blk = Column(Float, nullable=True)

    # Metadata
    stats_updated_at = Column(DateTime(timezone=True), nullable=True)

    players = relationship("Player", back_populates="team")

class Player(Base):
    __tablename__ = "players"
    id = Column(Integer, primary_key=True, index=True)
    nba_player_id = Column(Integer, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"))
    is_active = Column(Boolean, default=True)

    # Injury status from ESPN
    injury_status = Column(String(20), nullable=True)
    injury_return_date = Column(String(20), nullable=True)
    injury_details = Column(String(500), nullable=True)

    team = relationship("Team", back_populates="players")
    fantasy_scores = relationship("FantasyScore", back_populates="player", cascade="all, delete-orphan")

class Game(Base):
    __tablename__ = "games"
    id = Column(Integer, primary_key=True, index=True)
    nba_game_id = Column(String, unique=True, nullable=False, index=True)
    home_team_id = Column(Integer, ForeignKey("teams.id"))
    away_team_id = Column(Integer, ForeignKey("teams.id"))
    game_date = Column(Date, nullable=False, index=True)
    status = Column(String, default="scheduled")  # scheduled | live | final
    home_score = Column(Integer, nullable=True)
    away_score = Column(Integer, nullable=True)
    start_time_utc = Column(DateTime(timezone=True), nullable=True)

    home_team = relationship("Team", foreign_keys=[home_team_id])
    away_team = relationship("Team", foreign_keys=[away_team_id])

class FantasyScore(Base):
    __tablename__ = "fantasy_scores"
    __table_args__ = (UniqueConstraint("player_id", "game_id", name="uq_player_game"),)

    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    fantasy_score = Column(Integer, nullable=True)
    minutes = Column(Integer, nullable=True)  # Minutes played; 0 or NULL = DNP
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    player = relationship("Player", back_populates="fantasy_scores")
    game = relationship("Game")

class AppMetadata(Base):
    __tablename__ = "app_metadata"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, nullable=False, index=True)
    value = Column(String, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# --- Auth, picks, and notifications (Month 1 foundations) ---

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=True)
    hashed_password = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # soft-delete; filter WHERE deleted_at IS NULL

    owner = relationship("Owner", back_populates="user", uselist=False)
    devices = relationship("UserDevice", back_populates="user")
    notification_pref = relationship("NotificationPref", back_populates="user", uselist=False)
    notification_logs = relationship("NotificationLog", back_populates="user")
    entitlements = relationship("Entitlement", back_populates="user")


class AnonIdentity(Base):
    """Persistent anonymous identity. Token (server-generated UUID) is stored in a cookie.
    Outlives any single browser session — the pick history belongs to whoever holds the token.
    No push notifications for anonymous identities; register as a user to receive alerts."""
    __tablename__ = "anon_identities"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen = Column(DateTime(timezone=True), nullable=True, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # soft-delete for GDPR erasure

    owner = relationship("Owner", back_populates="identity", uselist=False)


class Owner(Base):
    """Pick-ownership abstraction. One row per identity (user OR anonymous identity).

    user_id UNIQUE is intentional: a user has exactly one canonical pick history,
    regardless of how many devices they use. Multi-device push is handled by UserDevice.

    Guest → user migration: UPDATE owners SET user_id = ?, identity_id = NULL in one
    transaction. All downstream picks follow automatically — no pick rows need to change.

    Future analytics/leaderboards: add is_public / display_name here without touching picks.
    """
    __tablename__ = "owners"
    __table_args__ = (
        CheckConstraint(
            "(user_id IS NOT NULL AND identity_id IS NULL) OR "
            "(user_id IS NULL AND identity_id IS NOT NULL)",
            name="ck_owner_single_identity",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=True)
    identity_id = Column(Integer, ForeignKey("anon_identities.id"), unique=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="owner")
    identity = relationship("AnonIdentity", back_populates="owner")
    picks = relationship("Pick", back_populates="owner")


class Pick(Base):
    """One pick per owner per game_date.

    Index strategy:
    - uq_pick_owner_date (unique constraint) covers (owner_id, game_date) — 30-day rule + dedup.
    - ix_pick_game_date covers game_date alone — leaderboard / daily summary queries.
    """
    __tablename__ = "picks"
    __table_args__ = (
        UniqueConstraint("owner_id", "game_date", name="uq_pick_owner_date"),
        Index("ix_pick_game_date", "game_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("owners.id"), nullable=False)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    game_date = Column(Date, nullable=False)
    picked_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("Owner", back_populates="picks")
    player = relationship("Player")


class UserDevice(Base):
    """Push token registration. One user → N devices; all active devices receive notifications.
    Set revoked_at when the user logs out of a device or explicitly disables push on it."""
    __tablename__ = "user_devices"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    push_token = Column(String, unique=True, nullable=False)
    platform = Column(String(10), nullable=False)  # ios | android | web
    registered_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen = Column(DateTime(timezone=True), nullable=True, index=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)  # NULL = active

    user = relationship("User", back_populates="devices")


class NotificationPref(Base):
    """One preference row per user. Anonymous identities do not receive notifications."""
    __tablename__ = "notification_prefs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    injury_alerts = Column(Boolean, default=True, nullable=False)
    deadline_alerts = Column(Boolean, default=True, nullable=False)

    user = relationship("User", back_populates="notification_pref")


class NotificationLog(Base):
    """Append-only audit log for sent notifications. Used for dedup (check before sending).

    Growth strategy: once rows exceed ~1M, partition by sent_at month using PostgreSQL
    declarative partitioning (ALTER TABLE … PARTITION BY RANGE). No schema change needed
    on this model — partitioning is transparent to SQLAlchemy queries.
    """
    __tablename__ = "notification_log"
    __table_args__ = (
        # Composite index for the dedup query: "did we send this type to this user today?"
        Index("ix_notif_log_user_sent", "user_id", "sent_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(SAEnum(NotificationType, native_enum=False), nullable=False)
    payload = Column(JSON, nullable=True)
    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(SAEnum(NotificationStatus, native_enum=False), nullable=False, default=NotificationStatus.sent)

    user = relationship("User", back_populates="notification_logs")


class Entitlement(Base):
    """Post-launch monetization placeholder. Always user-based — anonymous identities cannot purchase."""
    __tablename__ = "entitlements"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    product_id = Column(String(100), nullable=False)
    source = Column(SAEnum(EntitlementSource, native_enum=False), nullable=False)
    external_id = Column(String(200), nullable=True)
    granted_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)  # NULL = lifetime purchase
    status = Column(SAEnum(EntitlementStatus, native_enum=False), nullable=False, default=EntitlementStatus.active)

    user = relationship("User", back_populates="entitlements")
