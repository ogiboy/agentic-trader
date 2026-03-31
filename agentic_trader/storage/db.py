from datetime import datetime, timezone
from typing import Any

import duckdb

from agentic_trader.config import Settings
from agentic_trader.schemas import InvestmentPreferences, PortfolioSnapshot, PositionSnapshot, RunArtifacts

type OrderRow = tuple[str, str, str, str, bool, float, float, float, float, float]


class TradingDatabase:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.path = settings.database_path
        self.conn = duckdb.connect(str(self.path))
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.execute(
            """
            create table if not exists runs (
                run_id varchar primary key,
                created_at varchar not null,
                symbol varchar not null,
                interval varchar not null,
                approved boolean not null,
                payload_json varchar not null
            )
            """
        )
        self.conn.execute(
            """
            create table if not exists orders (
                order_id varchar primary key,
                created_at varchar not null,
                symbol varchar not null,
                side varchar not null,
                approved boolean not null,
                entry_price double not null,
                stop_loss double not null,
                take_profit double not null,
                position_size_pct double not null,
                confidence double not null,
                rationale varchar not null
            )
            """
        )
        self.conn.execute(
            """
            create table if not exists account_state (
                account_id varchar primary key,
                updated_at varchar not null,
                cash double not null,
                realized_pnl double not null
            )
            """
        )
        self.conn.execute(
            """
            create table if not exists positions (
                symbol varchar primary key,
                quantity double not null,
                average_price double not null,
                market_price double not null,
                updated_at varchar not null
            )
            """
        )
        self.conn.execute(
            """
            create table if not exists fills (
                fill_id varchar primary key,
                order_id varchar not null,
                created_at varchar not null,
                symbol varchar not null,
                side varchar not null,
                quantity double not null,
                price double not null,
                cash_delta double not null,
                realized_pnl_delta double not null
            )
            """
        )
        self.conn.execute(
            """
            create table if not exists preferences (
                profile_id varchar primary key,
                updated_at varchar not null,
                payload_json varchar not null
            )
            """
        )
        existing = self.conn.execute(
            "select count(*) from account_state where account_id = 'paper'"
        ).fetchone()
        if existing and int(existing[0]) == 0:
            self.conn.execute(
                """
                insert into account_state (account_id, updated_at, cash, realized_pnl)
                values ('paper', ?, ?, 0)
                """,
                [
                    datetime.now(timezone.utc).isoformat(),
                    self.settings.default_cash,
                ],
            )
        pref_existing = self.conn.execute(
            "select count(*) from preferences where profile_id = 'default'"
        ).fetchone()
        if pref_existing and int(pref_existing[0]) == 0:
            self.save_preferences(InvestmentPreferences())

    def insert_run(self, run_id: str, artifacts: RunArtifacts) -> None:
        self.conn.execute(
            """
            insert into runs (run_id, created_at, symbol, interval, approved, payload_json)
            values (?, ?, ?, ?, ?, ?)
            """,
            [
                run_id,
                datetime.now(timezone.utc).isoformat(),
                artifacts.snapshot.symbol,
                artifacts.snapshot.interval,
                artifacts.execution.approved,
                artifacts.model_dump_json(indent=2),
            ],
        )

    def insert_order(self, order: dict[str, Any]) -> None:
        self.conn.execute(
            """
            insert into orders (
                order_id, created_at, symbol, side, approved, entry_price,
                stop_loss, take_profit, position_size_pct, confidence, rationale
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                order["order_id"],
                order["created_at"],
                order["symbol"],
                order["side"],
                order["approved"],
                order["entry_price"],
                order["stop_loss"],
                order["take_profit"],
                order["position_size_pct"],
                order["confidence"],
                order["rationale"],
            ],
        )

    def latest_order(self) -> OrderRow | None:
        result = self.conn.execute(
            """
            select order_id, created_at, symbol, side, approved, entry_price,
                   stop_loss, take_profit, position_size_pct, confidence
            from orders
            order by created_at desc
            limit 1
            """
        ).fetchone()
        if result is None:
            return None

        return (
            str(result[0]),
            str(result[1]),
            str(result[2]),
            str(result[3]),
            bool(result[4]),
            float(result[5]),
            float(result[6]),
            float(result[7]),
            float(result[8]),
            float(result[9]),
        )

    def save_preferences(self, preferences: InvestmentPreferences) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            """
            insert into preferences (profile_id, updated_at, payload_json)
            values ('default', ?, ?)
            on conflict(profile_id) do update set
                updated_at = excluded.updated_at,
                payload_json = excluded.payload_json
            """,
            [now, preferences.model_dump_json(indent=2)],
        )

    def load_preferences(self) -> InvestmentPreferences:
        row = self.conn.execute(
            """
            select payload_json
            from preferences
            where profile_id = 'default'
            """
        ).fetchone()
        if row is None:
            preferences = InvestmentPreferences()
            self.save_preferences(preferences)
            return preferences
        return InvestmentPreferences.model_validate_json(str(row[0]))

    def list_recent_runs(self, limit: int = 10) -> list[tuple[str, str, str, str, bool]]:
        rows = self.conn.execute(
            """
            select run_id, created_at, symbol, interval, approved
            from runs
            order by created_at desc
            limit ?
            """,
            [limit],
        ).fetchall()
        recent: list[tuple[str, str, str, str, bool]] = []
        for row in rows:
            recent.append(
                (
                    str(row[0]),
                    str(row[1]),
                    str(row[2]),
                    str(row[3]),
                    bool(row[4]),
                )
            )
        return recent

    def get_account_snapshot(self) -> PortfolioSnapshot:
        row = self.conn.execute(
            """
            select cash, realized_pnl
            from account_state
            where account_id = 'paper'
            """
        ).fetchone()
        if row is None:
            raise RuntimeError("Paper account state is missing")

        positions = self.list_positions()
        market_value = sum(position.quantity * position.market_price for position in positions)
        unrealized_pnl = sum(position.unrealized_pnl for position in positions)
        cash = float(row[0])
        realized_pnl = float(row[1])
        equity = cash + market_value
        return PortfolioSnapshot(
            cash=cash,
            market_value=market_value,
            equity=equity,
            realized_pnl=realized_pnl,
            unrealized_pnl=unrealized_pnl,
            open_positions=len(positions),
        )

    def get_position(self, symbol: str) -> PositionSnapshot | None:
        row = self.conn.execute(
            """
            select symbol, quantity, average_price, market_price
            from positions
            where symbol = ?
            """,
            [symbol],
        ).fetchone()
        if row is None:
            return None

        quantity = float(row[1])
        average_price = float(row[2])
        market_price = float(row[3])
        market_value = quantity * market_price
        unrealized_pnl = (market_price - average_price) * quantity
        return PositionSnapshot(
            symbol=str(row[0]),
            quantity=quantity,
            average_price=average_price,
            market_price=market_price,
            market_value=market_value,
            unrealized_pnl=unrealized_pnl,
        )

    def list_positions(self) -> list[PositionSnapshot]:
        rows = self.conn.execute(
            """
            select symbol, quantity, average_price, market_price
            from positions
            where abs(quantity) > 0
            order by symbol
            """
        ).fetchall()
        positions: list[PositionSnapshot] = []
        for row in rows:
            quantity = float(row[1])
            average_price = float(row[2])
            market_price = float(row[3])
            positions.append(
                PositionSnapshot(
                    symbol=str(row[0]),
                    quantity=quantity,
                    average_price=average_price,
                    market_price=market_price,
                    market_value=quantity * market_price,
                    unrealized_pnl=(market_price - average_price) * quantity,
                )
            )
        return positions

    def apply_fill(
        self,
        *,
        fill_id: str,
        order_id: str,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        cash_delta: float,
        realized_pnl_delta: float,
        new_quantity: float,
        new_average_price: float,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            """
            insert into fills (
                fill_id, order_id, created_at, symbol, side, quantity, price,
                cash_delta, realized_pnl_delta
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                fill_id,
                order_id,
                now,
                symbol,
                side,
                quantity,
                price,
                cash_delta,
                realized_pnl_delta,
            ],
        )
        self.conn.execute(
            """
            update account_state
            set updated_at = ?, cash = cash + ?, realized_pnl = realized_pnl + ?
            where account_id = 'paper'
            """,
            [now, cash_delta, realized_pnl_delta],
        )
        self.conn.execute(
            """
            insert into positions (symbol, quantity, average_price, market_price, updated_at)
            values (?, ?, ?, ?, ?)
            on conflict(symbol) do update set
                quantity = excluded.quantity,
                average_price = excluded.average_price,
                market_price = excluded.market_price,
                updated_at = excluded.updated_at
            """,
            [symbol, new_quantity, new_average_price, price, now],
        )

    def mark_price(self, symbol: str, market_price: float) -> None:
        self.conn.execute(
            """
            update positions
            set market_price = ?, updated_at = ?
            where symbol = ?
            """,
            [market_price, datetime.now(timezone.utc).isoformat(), symbol],
        )
