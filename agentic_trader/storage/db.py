from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import duckdb

from agentic_trader.config import Settings
from agentic_trader.schemas import (
    AccountMark,
    DailyRiskReport,
    InvestmentPreferences,
    PortfolioSnapshot,
    PositionPlanSnapshot,
    PositionSnapshot,
    PositionExitDecision,
    RunRecord,
    RunArtifacts,
    ServiceEvent,
    ServiceStateSnapshot,
    TradeJournalEntry,
)

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
            create table if not exists position_plans (
                symbol varchar primary key,
                side varchar not null,
                entry_price double not null,
                stop_loss double not null,
                take_profit double not null,
                max_holding_bars integer not null,
                holding_bars integer not null,
                invalidation_logic varchar not null,
                updated_at varchar not null
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
        self.conn.execute(
            """
            create table if not exists account_marks (
                mark_id varchar primary key,
                created_at varchar not null,
                source varchar not null,
                note varchar not null,
                cycle_count integer,
                symbol varchar,
                cash double not null,
                market_value double not null,
                equity double not null,
                realized_pnl double not null,
                unrealized_pnl double not null,
                open_positions integer not null
            )
            """
        )
        self.conn.execute(
            """
            create table if not exists trade_journal (
                trade_id varchar primary key,
                opened_at varchar not null,
                closed_at varchar,
                symbol varchar not null,
                run_id varchar,
                entry_order_id varchar not null,
                exit_order_id varchar,
                planned_side varchar not null,
                approved boolean not null,
                journal_status varchar not null,
                entry_price double not null,
                exit_price double,
                stop_loss double not null,
                take_profit double not null,
                position_size_pct double not null,
                confidence double not null,
                coordinator_focus varchar not null,
                strategy_family varchar not null,
                manager_bias varchar not null,
                review_summary varchar not null,
                exit_reason varchar,
                realized_pnl double,
                notes varchar not null
            )
            """
        )
        self.conn.execute(
            """
            create table if not exists service_state (
                service_name varchar primary key,
                state varchar not null,
                updated_at varchar not null,
                started_at varchar,
                last_heartbeat_at varchar,
                continuous boolean not null,
                poll_seconds integer,
                cycle_count integer not null,
                current_symbol varchar,
                last_error varchar,
                pid bigint,
                stop_requested boolean not null default false,
                message varchar not null
            )
            """
        )
        service_columns = {
            str(row[1])
            for row in self.conn.execute("pragma table_info('service_state')").fetchall()
        }
        if "pid" not in service_columns:
            self.conn.execute("alter table service_state add column pid bigint")
        if "stop_requested" not in service_columns:
            self.conn.execute("alter table service_state add column stop_requested boolean not null default false")
        self.conn.execute(
            """
            create table if not exists service_events (
                event_id varchar primary key,
                created_at varchar not null,
                service_name varchar not null,
                level varchar not null,
                event_type varchar not null,
                message varchar not null,
                cycle_count integer,
                symbol varchar
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

    def get_run(self, run_id: str) -> RunRecord | None:
        row = self.conn.execute(
            """
            select run_id, created_at, symbol, interval, approved, payload_json
            from runs
            where run_id = ?
            """,
            [run_id],
        ).fetchone()
        if row is None:
            return None
        return RunRecord(
            run_id=str(row[0]),
            created_at=str(row[1]),
            symbol=str(row[2]),
            interval=str(row[3]),
            approved=bool(row[4]),
            artifacts=RunArtifacts.model_validate_json(str(row[5])),
        )

    def latest_run(self) -> RunRecord | None:
        row = self.conn.execute(
            """
            select run_id
            from runs
            order by created_at desc
            limit 1
            """
        ).fetchone()
        if row is None:
            return None
        return self.get_run(str(row[0]))

    def record_account_mark(
        self,
        *,
        source: str,
        note: str,
        cycle_count: int | None = None,
        symbol: str | None = None,
    ) -> str:
        snapshot = self.get_account_snapshot()
        mark_id = f"mark-{uuid4().hex[:12]}"
        self.conn.execute(
            """
            insert into account_marks (
                mark_id, created_at, source, note, cycle_count, symbol,
                cash, market_value, equity, realized_pnl, unrealized_pnl, open_positions
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                mark_id,
                datetime.now(timezone.utc).isoformat(),
                source,
                note,
                cycle_count,
                symbol,
                snapshot.cash,
                snapshot.market_value,
                snapshot.equity,
                snapshot.realized_pnl,
                snapshot.unrealized_pnl,
                snapshot.open_positions,
            ],
        )
        return mark_id

    def list_account_marks(self, limit: int = 20) -> list[AccountMark]:
        rows = self.conn.execute(
            """
            select mark_id, created_at, source, note, cycle_count, symbol,
                   cash, market_value, equity, realized_pnl, unrealized_pnl, open_positions
            from account_marks
            order by created_at desc
            limit ?
            """,
            [limit],
        ).fetchall()
        marks: list[AccountMark] = []
        for row in rows:
            marks.append(
                AccountMark(
                    mark_id=str(row[0]),
                    created_at=str(row[1]),
                    source=str(row[2]),
                    note=str(row[3]),
                    cycle_count=int(row[4]) if row[4] is not None else None,
                    symbol=str(row[5]) if row[5] is not None else None,
                    cash=float(row[6]),
                    market_value=float(row[7]),
                    equity=float(row[8]),
                    realized_pnl=float(row[9]),
                    unrealized_pnl=float(row[10]),
                    open_positions=int(row[11]),
                )
            )
        return marks

    def order_has_fill(self, order_id: str) -> bool:
        row = self.conn.execute(
            """
            select count(*)
            from fills
            where order_id = ?
            """,
            [order_id],
        ).fetchone()
        return bool(row and int(row[0]) > 0)

    def order_realized_pnl(self, order_id: str) -> float:
        row = self.conn.execute(
            """
            select coalesce(sum(realized_pnl_delta), 0)
            from fills
            where order_id = ?
            """,
            [order_id],
        ).fetchone()
        if row is None:
            return 0.0
        return float(row[0])

    def create_trade_journal(
        self,
        *,
        run_id: str | None,
        order_id: str,
        artifacts: RunArtifacts,
        journal_status: str,
        notes: str = "",
    ) -> str:
        trade_id = f"trade-{uuid4().hex[:12]}"
        self.conn.execute(
            """
            insert into trade_journal (
                trade_id, opened_at, symbol, run_id, entry_order_id, planned_side,
                approved, journal_status, entry_price, stop_loss, take_profit,
                position_size_pct, confidence, coordinator_focus, strategy_family,
                manager_bias, review_summary, notes
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                trade_id,
                datetime.now(timezone.utc).isoformat(),
                artifacts.snapshot.symbol,
                run_id,
                order_id,
                artifacts.execution.side,
                artifacts.execution.approved,
                journal_status,
                artifacts.execution.entry_price,
                artifacts.execution.stop_loss,
                artifacts.execution.take_profit,
                artifacts.execution.position_size_pct,
                artifacts.execution.confidence,
                artifacts.coordinator.market_focus,
                artifacts.strategy.strategy_family,
                artifacts.manager.action_bias,
                artifacts.review.summary,
                notes,
            ],
        )
        return trade_id

    def close_trade_journal(
        self,
        *,
        symbol: str,
        exit_order_id: str,
        exit_reason: str,
        exit_price: float,
        realized_pnl: float,
        notes: str = "",
    ) -> None:
        row = self.conn.execute(
            """
            select trade_id
            from trade_journal
            where symbol = ? and journal_status = 'open'
            order by opened_at desc
            limit 1
            """,
            [symbol],
        ).fetchone()
        if row is None:
            return
        self.conn.execute(
            """
            update trade_journal
            set closed_at = ?,
                exit_order_id = ?,
                journal_status = 'closed',
                exit_price = ?,
                exit_reason = ?,
                realized_pnl = ?,
                notes = case
                    when notes = '' then ?
                    else notes || ' ' || ?
                end
            where trade_id = ?
            """,
            [
                datetime.now(timezone.utc).isoformat(),
                exit_order_id,
                exit_price,
                exit_reason,
                realized_pnl,
                notes,
                notes,
                str(row[0]),
            ],
        )

    def list_trade_journal(self, limit: int = 20) -> list[TradeJournalEntry]:
        rows = self.conn.execute(
            """
            select trade_id, opened_at, closed_at, symbol, run_id, entry_order_id, exit_order_id,
                   planned_side, approved, journal_status, entry_price, exit_price, stop_loss,
                   take_profit, position_size_pct, confidence, coordinator_focus, strategy_family,
                   manager_bias, review_summary, exit_reason, realized_pnl, notes
            from trade_journal
            order by opened_at desc
            limit ?
            """,
            [limit],
        ).fetchall()
        entries: list[TradeJournalEntry] = []
        for row in rows:
            entries.append(
                TradeJournalEntry(
                    trade_id=str(row[0]),
                    opened_at=str(row[1]),
                    closed_at=str(row[2]) if row[2] is not None else None,
                    symbol=str(row[3]),
                    run_id=str(row[4]) if row[4] is not None else None,
                    entry_order_id=str(row[5]),
                    exit_order_id=str(row[6]) if row[6] is not None else None,
                    planned_side=str(row[7]),
                    approved=bool(row[8]),
                    journal_status=str(row[9]),
                    entry_price=float(row[10]),
                    exit_price=float(row[11]) if row[11] is not None else None,
                    stop_loss=float(row[12]),
                    take_profit=float(row[13]),
                    position_size_pct=float(row[14]),
                    confidence=float(row[15]),
                    coordinator_focus=str(row[16]),
                    strategy_family=str(row[17]),
                    manager_bias=str(row[18]),
                    review_summary=str(row[19]),
                    exit_reason=str(row[20]) if row[20] is not None else None,
                    realized_pnl=float(row[21]) if row[21] is not None else None,
                    notes=str(row[22]),
                )
            )
        return entries

    def build_daily_risk_report(self, report_date: str | None = None) -> DailyRiskReport:
        resolved_date = report_date or datetime.now(timezone.utc).date().isoformat()
        snapshot = self.get_account_snapshot()
        positions = self.list_positions()
        fills_row = self.conn.execute(
            """
            select count(*), coalesce(sum(realized_pnl_delta), 0)
            from fills
            where created_at like ?
            """,
            [f"{resolved_date}%"],
        ).fetchone()
        marks_row = self.conn.execute(
            """
            select count(*), coalesce(max(equity), 0)
            from account_marks
            where created_at like ?
            """,
            [f"{resolved_date}%"],
        ).fetchone()
        peak_row = self.conn.execute(
            """
            select coalesce(max(equity), 0)
            from account_marks
            """
        ).fetchone()
        fills_today = int(fills_row[0]) if fills_row is not None else 0
        daily_realized_pnl = float(fills_row[1]) if fills_row is not None else 0.0
        marks_recorded = int(marks_row[0]) if marks_row is not None else 0
        all_time_peak = float(peak_row[0]) if peak_row is not None else snapshot.equity
        gross_exposure = sum(abs(position.market_value) for position in positions)
        largest_position = max((abs(position.market_value) for position in positions), default=0.0)
        equity = snapshot.equity if snapshot.equity != 0 else 1.0
        drawdown_from_peak_pct = max(0.0, (all_time_peak - snapshot.equity) / all_time_peak) if all_time_peak > 0 else 0.0

        warnings: list[str] = []
        if snapshot.open_positions >= 5:
            warnings.append("Open position count is elevated.")
        if gross_exposure / equity > 0.8:
            warnings.append("Gross exposure is above 80% of equity.")
        if drawdown_from_peak_pct > 0.1:
            warnings.append("Portfolio drawdown from peak is above 10%.")

        return DailyRiskReport(
            report_date=resolved_date,
            generated_at=datetime.now(timezone.utc).isoformat(),
            cash=snapshot.cash,
            market_value=snapshot.market_value,
            equity=snapshot.equity,
            realized_pnl=snapshot.realized_pnl,
            unrealized_pnl=snapshot.unrealized_pnl,
            open_positions=snapshot.open_positions,
            fills_today=fills_today,
            marks_recorded=marks_recorded,
            daily_realized_pnl=daily_realized_pnl,
            gross_exposure_pct=gross_exposure / equity,
            largest_position_pct=largest_position / equity,
            drawdown_from_peak_pct=drawdown_from_peak_pct,
            warnings=warnings,
        )

    def upsert_service_state(
        self,
        *,
        service_name: str = "orchestrator",
        state: str,
        continuous: bool,
        poll_seconds: int | None,
        cycle_count: int,
        current_symbol: str | None,
        message: str,
        last_error: str | None = None,
        pid: int | None = None,
        stop_requested: bool | None = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        existing = self.get_service_state(service_name)
        started_at = existing.started_at if existing is not None else None
        if state == "starting" or started_at is None:
            started_at = now
        resolved_pid = pid if pid is not None else (existing.pid if existing is not None else None)
        resolved_stop_requested = (
            stop_requested if stop_requested is not None else (existing.stop_requested if existing is not None else False)
        )

        self.conn.execute(
            """
            insert into service_state (
                service_name, state, updated_at, started_at, last_heartbeat_at,
                continuous, poll_seconds, cycle_count, current_symbol, last_error, pid, stop_requested, message
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(service_name) do update set
                state = excluded.state,
                updated_at = excluded.updated_at,
                started_at = excluded.started_at,
                last_heartbeat_at = excluded.last_heartbeat_at,
                continuous = excluded.continuous,
                poll_seconds = excluded.poll_seconds,
                cycle_count = excluded.cycle_count,
                current_symbol = excluded.current_symbol,
                last_error = excluded.last_error,
                pid = excluded.pid,
                stop_requested = excluded.stop_requested,
                message = excluded.message
            """,
            [
                service_name,
                state,
                now,
                started_at,
                now,
                continuous,
                poll_seconds,
                cycle_count,
                current_symbol,
                last_error,
                resolved_pid,
                resolved_stop_requested,
                message,
            ],
        )

    def get_service_state(self, service_name: str = "orchestrator") -> ServiceStateSnapshot | None:
        row = self.conn.execute(
            """
            select service_name, state, updated_at, started_at, last_heartbeat_at,
                   continuous, poll_seconds, cycle_count, current_symbol, last_error, pid, stop_requested, message
            from service_state
            where service_name = ?
            """,
            [service_name],
        ).fetchone()
        if row is None:
            return None
        return ServiceStateSnapshot(
            service_name=str(row[0]),
            state=str(row[1]),
            updated_at=str(row[2]),
            started_at=str(row[3]) if row[3] is not None else None,
            last_heartbeat_at=str(row[4]) if row[4] is not None else None,
            continuous=bool(row[5]),
            poll_seconds=int(row[6]) if row[6] is not None else None,
            cycle_count=int(row[7]),
            current_symbol=str(row[8]) if row[8] is not None else None,
            last_error=str(row[9]) if row[9] is not None else None,
            pid=int(row[10]) if row[10] is not None else None,
            stop_requested=bool(row[11]),
            message=str(row[12]),
        )

    def request_stop_service(self, service_name: str = "orchestrator") -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            """
            update service_state
            set stop_requested = true,
                state = 'stopping',
                updated_at = ?,
                last_heartbeat_at = ?,
                message = 'Stop requested by operator.'
            where service_name = ?
            """,
            [now, now, service_name],
        )

    def clear_stop_request(self, service_name: str = "orchestrator") -> None:
        self.conn.execute(
            """
            update service_state
            set stop_requested = false
            where service_name = ?
            """,
            [service_name],
        )

    def insert_service_event(
        self,
        *,
        service_name: str = "orchestrator",
        level: str,
        event_type: str,
        message: str,
        cycle_count: int | None = None,
        symbol: str | None = None,
    ) -> str:
        event_id = f"evt-{uuid4().hex[:12]}"
        self.conn.execute(
            """
            insert into service_events (
                event_id, created_at, service_name, level, event_type, message, cycle_count, symbol
            )
            values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                event_id,
                datetime.now(timezone.utc).isoformat(),
                service_name,
                level,
                event_type,
                message,
                cycle_count,
                symbol,
            ],
        )
        return event_id

    def list_service_events(self, limit: int = 20, service_name: str = "orchestrator") -> list[ServiceEvent]:
        rows = self.conn.execute(
            """
            select event_id, created_at, level, event_type, message, cycle_count, symbol
            from service_events
            where service_name = ?
            order by created_at desc
            limit ?
            """,
            [service_name, limit],
        ).fetchall()
        events: list[ServiceEvent] = []
        for row in rows:
            events.append(
                ServiceEvent(
                    event_id=str(row[0]),
                    created_at=str(row[1]),
                    level=str(row[2]),
                    event_type=str(row[3]),
                    message=str(row[4]),
                    cycle_count=int(row[5]) if row[5] is not None else None,
                    symbol=str(row[6]) if row[6] is not None else None,
                )
            )
        return events

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

    def save_position_plan(
        self,
        *,
        symbol: str,
        side: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        max_holding_bars: int,
        holding_bars: int,
        invalidation_logic: str,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            """
            insert into position_plans (
                symbol, side, entry_price, stop_loss, take_profit,
                max_holding_bars, holding_bars, invalidation_logic, updated_at
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(symbol) do update set
                side = excluded.side,
                entry_price = excluded.entry_price,
                stop_loss = excluded.stop_loss,
                take_profit = excluded.take_profit,
                max_holding_bars = excluded.max_holding_bars,
                holding_bars = excluded.holding_bars,
                invalidation_logic = excluded.invalidation_logic,
                updated_at = excluded.updated_at
            """,
            [
                symbol,
                side,
                entry_price,
                stop_loss,
                take_profit,
                max_holding_bars,
                holding_bars,
                invalidation_logic,
                now,
            ],
        )

    def get_position_plan(self, symbol: str) -> PositionPlanSnapshot | None:
        row = self.conn.execute(
            """
            select symbol, side, entry_price, stop_loss, take_profit,
                   max_holding_bars, holding_bars, invalidation_logic, updated_at
            from position_plans
            where symbol = ?
            """,
            [symbol],
        ).fetchone()
        if row is None:
            return None
        return PositionPlanSnapshot(
            symbol=str(row[0]),
            side=str(row[1]),
            entry_price=float(row[2]),
            stop_loss=float(row[3]),
            take_profit=float(row[4]),
            max_holding_bars=int(row[5]),
            holding_bars=int(row[6]),
            invalidation_logic=str(row[7]),
            updated_at=str(row[8]),
        )

    def list_position_plans(self) -> list[PositionPlanSnapshot]:
        rows = self.conn.execute(
            """
            select symbol, side, entry_price, stop_loss, take_profit,
                   max_holding_bars, holding_bars, invalidation_logic, updated_at
            from position_plans
            order by symbol
            """
        ).fetchall()
        plans: list[PositionPlanSnapshot] = []
        for row in rows:
            plans.append(
                PositionPlanSnapshot(
                    symbol=str(row[0]),
                    side=str(row[1]),
                    entry_price=float(row[2]),
                    stop_loss=float(row[3]),
                    take_profit=float(row[4]),
                    max_holding_bars=int(row[5]),
                    holding_bars=int(row[6]),
                    invalidation_logic=str(row[7]),
                    updated_at=str(row[8]),
                )
            )
        return plans

    def update_position_plan_holding(self, symbol: str, holding_bars: int) -> None:
        self.conn.execute(
            """
            update position_plans
            set holding_bars = ?, updated_at = ?
            where symbol = ?
            """,
            [holding_bars, datetime.now(timezone.utc).isoformat(), symbol],
        )

    def delete_position_plan(self, symbol: str) -> None:
        self.conn.execute(
            "delete from position_plans where symbol = ?",
            [symbol],
        )

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
