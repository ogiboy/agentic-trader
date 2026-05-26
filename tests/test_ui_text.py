from agentic_trader import ui_text


def test_get_ui_text_defaults_to_english_catalog() -> None:
    catalog = ui_text.get_ui_text()

    assert ui_text.SUPPORTED_UI_LOCALES == ("en", "tr")
    assert catalog.title_runtime_status == "Runtime Status"
    assert catalog.cli_app_help == ui_text.HELP_CLI_APP
    assert catalog.help_json == ui_text.HELP_JSON
    assert catalog.help_idea_preset == ui_text.HELP_IDEA_PRESET
    assert catalog.help_trade_side == ui_text.HELP_TRADE_SIDE
    assert catalog.help_trade_limit_price == ui_text.HELP_TRADE_LIMIT_PRICE
    assert catalog.title_execution_summary == ui_text.TITLE_EXECUTION_SUMMARY
    assert catalog.label_order_id == ui_text.LABEL_ORDER_ID
    assert catalog.label_live_process == ui_text.LABEL_LIVE_PROCESS
    assert catalog.message_fallback_used_in == ui_text.MESSAGE_FALLBACK_USED_IN
    assert catalog.message_no_runtime_state == ui_text.MESSAGE_NO_RUNTIME_STATE
    assert catalog.message_no_runtime_events == ui_text.MESSAGE_NO_RUNTIME_EVENTS
    assert catalog.title_trade_journal == ui_text.TITLE_TRADE_JOURNAL
    assert catalog.title_daily_risk_report == ui_text.TITLE_DAILY_RISK_REPORT
    assert catalog.title_run_review == ui_text.TITLE_RUN_REVIEW
    assert catalog.title_agent_trace == ui_text.TITLE_AGENT_TRACE
    assert catalog.title_walk_forward_backtest == ui_text.TITLE_WALK_FORWARD_BACKTEST
    assert catalog.label_closed_trades == ui_text.LABEL_CLOSED_TRADES
    assert catalog.list_separator == ui_text.UI_LIST_SEPARATOR
    assert catalog.db_locked_msg == ui_text.DB_LOCKED_MSG


def test_get_ui_text_supports_turkish_regional_locale() -> None:
    catalog = ui_text.get_ui_text("tr-TR")

    assert catalog.title_runtime_status == "Runtime Durumu"
    assert catalog.help_model_service_app.startswith("Istege bagli")
    assert catalog.help_idea_volume == "Son volume."
    assert catalog.help_trade_reference_price.startswith("Proposal icin")
    assert catalog.title_operator_instruction == "Operator Talimati"
    assert catalog.label_requires_confirmation == "Onay Gerektirir"
    assert catalog.label_live_process == "Canli Process"
    assert catalog.message_no_runtime_state.startswith("Henuz runtime")
    assert catalog.title_daily_risk_report == "Gunluk Risk Raporu"
    assert catalog.label_fills_today == "Bugunku Fill'ler"
    assert catalog.title_agent_decisions == "Agent Kararlari"
    assert catalog.label_output_preview == "Cikti Onizleme"
    assert catalog.title_backtest_comparison == "Backtest Karsilastirma"
    assert catalog.label_warmup_bars == "Warmup Bar'lari"
    assert catalog.prompt_select_action == "Aksiyon sec"
    assert catalog.style_key_column == ui_text.STYLE_KEY_COLUMN


def test_normalize_locale_falls_back_to_english() -> None:
    assert ui_text.normalize_locale(None) == "en"
    assert ui_text.normalize_locale("de-DE") == "en"
    assert ui_text.normalize_locale("tr") == "tr"
