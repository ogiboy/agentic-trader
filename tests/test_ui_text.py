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
    assert catalog.prompt_select_action == "Aksiyon sec"
    assert catalog.style_key_column == ui_text.STYLE_KEY_COLUMN


def test_normalize_locale_falls_back_to_english() -> None:
    assert ui_text.normalize_locale(None) == "en"
    assert ui_text.normalize_locale("de-DE") == "en"
    assert ui_text.normalize_locale("tr") == "tr"
