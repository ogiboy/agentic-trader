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
    assert (
        catalog.title_backtest_memory_ablation == ui_text.TITLE_BACKTEST_MEMORY_ABLATION
    )
    assert catalog.title_trade_proposals == ui_text.TITLE_TRADE_PROPOSALS
    assert catalog.message_no_trade_proposals == ui_text.MESSAGE_NO_TRADE_PROPOSALS
    assert catalog.title_finance_operations == ui_text.TITLE_FINANCE_OPERATIONS
    assert catalog.label_marked_at == ui_text.LABEL_MARKED_AT
    assert catalog.help_locale_override == ui_text.HELP_LOCALE_OVERRIDE
    assert catalog.title_runtime_mode == ui_text.TITLE_RUNTIME_MODE
    assert catalog.label_allowed == ui_text.LABEL_ALLOWED
    assert catalog.title_environment_check == ui_text.TITLE_ENVIRONMENT_CHECK
    assert catalog.label_llm_provider == ui_text.LABEL_LLM_PROVIDER
    assert catalog.title_setup_status == ui_text.TITLE_SETUP_STATUS
    assert catalog.label_core_ready == ui_text.LABEL_CORE_READY
    assert catalog.title_available_models == ui_text.TITLE_AVAILABLE_MODELS
    assert catalog.title_web_gui_service == ui_text.TITLE_WEB_GUI_SERVICE
    assert catalog.title_camofox_browser_helper == (
        ui_text.TITLE_CAMOFOX_BROWSER_HELPER
    )
    assert catalog.title_operator_launcher == ui_text.TITLE_OPERATOR_LAUNCHER
    assert catalog.message_setup_bootstrap_guidance == (
        ui_text.MESSAGE_SETUP_BOOTSTRAP_GUIDANCE
    )
    assert catalog.status_ready == ui_text.STATUS_READY
    assert catalog.title_model_pull == ui_text.TITLE_MODEL_PULL
    assert catalog.label_exit_code == ui_text.LABEL_EXIT_CODE
    assert catalog.help_webgui_open_browser == ui_text.HELP_WEBGUI_OPEN_BROWSER
    assert catalog.title_research_sidecar_status == (
        ui_text.TITLE_RESEARCH_SIDECAR_STATUS
    )
    assert catalog.label_last_successful_update == (
        ui_text.LABEL_LAST_SUCCESSFUL_UPDATE
    )
    assert catalog.title_research_cycle_control == ui_text.TITLE_RESEARCH_CYCLE_CONTROL
    assert catalog.label_sidecar_available == ui_text.LABEL_SIDECAR_AVAILABLE
    assert catalog.message_research_snapshot_recorded == (
        ui_text.MESSAGE_RESEARCH_SNAPSHOT_RECORDED
    )
    assert catalog.title_launch_plan == ui_text.TITLE_LAUNCH_PLAN
    assert catalog.help_launch_symbols == ui_text.HELP_LAUNCH_SYMBOLS
    assert catalog.message_runtime_gate_open == ui_text.MESSAGE_RUNTIME_GATE_OPEN
    assert catalog.list_separator == ui_text.UI_LIST_SEPARATOR
    assert catalog.db_locked_msg == ui_text.DB_LOCKED_MSG
    assert catalog.title_portfolio == ui_text.TITLE_PORTFOLIO
    assert catalog.title_positions == ui_text.TITLE_POSITIONS
    assert catalog.title_service_supervisor == ui_text.TITLE_SERVICE_SUPERVISOR
    assert catalog.label_average_price == ui_text.LABEL_AVERAGE_PRICE
    assert catalog.label_market_price == ui_text.LABEL_MARKET_PRICE
    assert catalog.label_quantity == ui_text.LABEL_QUANTITY
    assert catalog.message_no_open_positions == ui_text.MESSAGE_NO_OPEN_POSITIONS
    assert catalog.message_no_stdout_log_lines == (
        ui_text.MESSAGE_NO_STDOUT_LOG_LINES
    )
    assert catalog.message_no_stderr_log_lines == (
        ui_text.MESSAGE_NO_STDERR_LOG_LINES
    )
    assert catalog.title_broker_status == ui_text.TITLE_BROKER_STATUS
    assert catalog.title_provider_diagnostics == ui_text.TITLE_PROVIDER_DIAGNOSTICS
    assert catalog.title_provider_source_ladder == (
        ui_text.TITLE_PROVIDER_SOURCE_LADDER
    )
    assert catalog.label_adapter == ui_text.LABEL_ADAPTER
    assert catalog.label_default_model == ui_text.LABEL_DEFAULT_MODEL
    assert catalog.label_live_ready == ui_text.LABEL_LIVE_READY
    assert catalog.label_api_key == ui_text.LABEL_API_KEY
    assert catalog.status_pass == ui_text.STATUS_PASS
    assert catalog.status_fail == ui_text.STATUS_FAIL
    assert catalog.title_v1_readiness == ui_text.TITLE_V1_READINESS
    assert catalog.title_paper_operation_checks == (
        ui_text.TITLE_PAPER_OPERATION_CHECKS
    )
    assert catalog.title_alpaca_paper_checks == ui_text.TITLE_ALPACA_PAPER_CHECKS
    assert catalog.help_trade_proposals_limit == ui_text.HELP_TRADE_PROPOSALS_LIMIT
    assert catalog.help_proposal_candidates_limit == (
        ui_text.HELP_PROPOSAL_CANDIDATES_LIMIT
    )
    assert catalog.message_trade_proposals_temporarily_unavailable == (
        ui_text.MESSAGE_TRADE_PROPOSALS_TEMPORARILY_UNAVAILABLE
    )
    assert catalog.title_proposal_candidate_created == (
        ui_text.TITLE_PROPOSAL_CANDIDATE_CREATED
    )
    assert catalog.title_proposal_candidate_promoted == (
        ui_text.TITLE_PROPOSAL_CANDIDATE_PROMOTED
    )
    assert catalog.help_candidate_materiality == ui_text.HELP_CANDIDATE_MATERIALITY
    assert catalog.help_fetch_provider_news == ui_text.HELP_FETCH_PROVIDER_NEWS
    assert catalog.message_proposal_candidate_promoted == (
        ui_text.MESSAGE_PROPOSAL_CANDIDATE_PROMOTED
    )


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
    assert catalog.label_with_memory == "Hafiza Ile"
    assert catalog.title_trade_proposals == "Trade Proposal'lari"
    assert catalog.title_finance_operations_checks == "Finance Operations Kontrolleri"
    assert catalog.label_currency == "Para Birimi"
    assert catalog.help_locale_persist.startswith("Terminal UI locale")
    assert catalog.title_runtime_mode_transition_checklist.startswith("Runtime Mode")
    assert catalog.title_ui_locale == "UI Locale"
    assert catalog.label_supported == "Desteklenen"
    assert catalog.title_tool_readiness == "Tool Readiness"
    assert catalog.label_workspace == "Workspace"
    assert catalog.title_available_models == "Kullanilabilir Modeller"
    assert catalog.title_web_gui_service == "Web GUI Servisi"
    assert catalog.title_camofox_stderr_tail == "Camofox Stderr Kuyrugu"
    assert catalog.title_choose_surface == "Yuzey Sec"
    assert catalog.message_no_action_selected == "Aksiyon secilmedi."
    assert catalog.status_needs_attention == "dikkat gerekiyor"
    assert catalog.title_model_pull == "Model Cekme"
    assert catalog.title_camofox_start_failed == "Camofox Baslatma Basarisiz"
    assert catalog.help_model_service_port == "Tercih edilen app-managed Ollama portu."
    assert catalog.title_research_source_health == "Research Kaynak Sagligi"
    assert catalog.status_available == "kullanilabilir"
    assert catalog.title_recommended_commands == "Onerilen Komutlar"
    assert catalog.label_uv_available == "uv Kullanilabilir"
    assert catalog.title_launch_plan == "Baslatma Plani"
    assert catalog.message_launch_symbol_required == "En az bir sembol gereklidir."
    assert catalog.title_positions == "Pozisyonlar"
    assert catalog.title_service_stdout_tail == "Service Stdout Kuyrugu"
    assert catalog.label_average_price == "Ortalama Fiyat"
    assert catalog.label_market_price == "Piyasa Fiyati"
    assert catalog.label_quantity == "Miktar"
    assert catalog.message_no_open_positions == "Acik pozisyon yok."
    assert catalog.message_no_stdout_log_lines == "Henuz stdout log satiri yok."
    assert catalog.message_no_stderr_log_lines == "Henuz stderr log satiri yok."
    assert catalog.title_broker_status == "Broker Durumu"
    assert catalog.label_default_model == "Varsayilan Model"
    assert catalog.label_live_execution_enabled == "Live Execution Etkin"
    assert catalog.label_live_ready == "Live Hazir"
    assert catalog.label_alpaca_credentials_configured == (
        "Alpaca Credential'lari Ayarli"
    )
    assert catalog.title_paper_operation_checks == "Paper Operation Kontrolleri"
    assert catalog.title_alpaca_paper_checks == "Alpaca Paper Kontrolleri"
    assert catalog.help_trade_proposals_limit == (
        "Gosterilecek maksimum trade proposal sayisi."
    )
    assert catalog.message_v1_readiness_status_unavailable == (
        "V1 readiness durumu kullanilamiyor."
    )
    assert catalog.title_candidate_rejected == "Candidate Reddedildi"
    assert catalog.title_proposal_candidate_created == (
        "Proposal Candidate Olusturuldu"
    )
    assert catalog.help_candidate_source == "Candidate kaynagi."
    assert catalog.message_proposal_candidate_promoted.endswith(
        "Broker submission denenmedi."
    )
    assert catalog.prompt_select_action == "Aksiyon sec"
    assert catalog.style_key_column == ui_text.STYLE_KEY_COLUMN


def test_normalize_locale_falls_back_to_english() -> None:
    assert ui_text.normalize_locale(None) == "en"
    assert ui_text.normalize_locale("de-DE") == "en"
    assert ui_text.normalize_locale("tr") == "tr"
