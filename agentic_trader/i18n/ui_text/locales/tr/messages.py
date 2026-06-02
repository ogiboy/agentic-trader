"""TR terminal UI messages copy."""

from __future__ import annotations

TR_MESSAGES_COPY: dict[str, str] = {
    "db_locked_msg": "Runtime writer veritabaninin sahibi; biraz sonra tekrar deneyin.",
    "message_action_cancelled_returning": "Aksiyon iptal edildi. Control room'a donuluyor.",
    "message_all_agent_stages_llm_path": "Tum agent asamalari LLM yolu ile tamamlandi.",
    "message_background_service_not_active": "Su anda aktif managed service yok.",
    "message_background_service_restarted": "Background orchestrator PID {pid} ile yeniden baslatildi.",
    "message_control_room_closed": "Control room temiz kapandi.",
    "message_fallback_used_in": "Fallback kullanilan asamalar",
    "message_evidence_bundle_written": "Bundle {bundle_dir} icine yazildi",
    "message_no_elevated_portfolio_risk_warnings": "Bu rapor icin yuksek portfoy risk uyarisi yok.",
    "message_no_runtime_state": "Henuz runtime durumu kaydedilmedi.",
    "message_no_runtime_events": "Henuz runtime olayi kaydedilmedi.",
    "message_no_runs_recorded": "Henuz run kaydi yok.",
    "message_no_stderr_log_lines": "Henuz stderr log satiri yok.",
    "message_no_stdout_log_lines": "Henuz stdout log satiri yok.",
    "message_no_trade_journal_entries": "Henuz trade journal kaydi yok.",
    "message_no_historical_memories": "Henuz historical memory yok.",
    "message_no_orders_recorded": "Henuz order kaydi yok.",
    "message_no_agent_activity_recorded": "Henuz agent activity kaydi yok.",
    "message_no_live_agent_stage_events": "Henuz live agent stage event yok.",
    "message_memory_explorer_temporarily_unavailable": "Memory explorer gecici olarak kullanilamiyor.\n\n{error}",
    "message_no_action_selected": "Aksiyon secilmedi.",
    "message_no_retrieval_inspection_context": "Retrieval inspection icin henuz agent trace context yok.",
    "message_no_retrieval_stage_context": "Bu asama icin retrieval veya memory context eklenmemis.",
    "message_trade_journal_temporarily_unavailable": "Runtime writer veritabaninin sahibiyken trade journal gecici olarak "
    "kullanilamiyor.\n\n{error}",
    "message_risk_report_temporarily_unavailable": "Runtime writer veritabaninin sahibiyken risk report gecici olarak "
    "kullanilamiyor.\n\n{error}",
    "message_run_review_temporarily_unavailable": "Runtime writer veritabaninin sahibiyken run review gecici olarak "
    "kullanilamiyor.\n\n{error}",
    "message_no_persisted_runs_review": "Review icin persisted run yok.",
    "message_run_trace_temporarily_unavailable": "Runtime writer veritabaninin sahibiyken run trace gecici olarak "
    "kullanilamiyor.\n\n{error}",
    "message_no_persisted_runs_trace": "Trace icin persisted run yok.",
    "message_trade_context_temporarily_unavailable": "Runtime writer veritabaninin sahibiyken trade context gecici olarak "
    "kullanilamiyor.\n\n{error}",
    "message_no_trade_context": "Henuz persisted trade context yok.",
    "message_run_replay_temporarily_unavailable": "Runtime writer veritabaninin sahibiyken run replay gecici olarak "
    "kullanilamiyor.\n\n{error}",
    "message_no_persisted_runs_replay": "Replay icin persisted run yok.",
    "message_no_persisted_runs_export": "Export icin persisted run yok.",
    "message_chat_exit_hint": "Chat'ten cikmak icin /exit yazin.",
    "message_final_stage_update": "Son stage update: {latest_message}\n\n{artifacts_json}",
    "message_preferences_saved": "Preferences kaydedildi.",
    "message_preparing_symbol": "{symbol} hazirlaniyor.",
    "message_run_report_written": "Run report {output} icine yazildi.",
    "message_retrieval_inspection_temporarily_unavailable": "Retrieval inspection gecici olarak kullanilamiyor.\n\n{error}",
    "message_backtest_choose_one_comparison": "Tek run icin --compare-baseline veya --compare-memory secin.",
    "message_backtest_comparison_written": "Backtest comparison {output} icine yazildi.",
    "message_backtest_memory_ablation_written": "Backtest memory ablation {output} icine yazildi.",
    "message_backtest_summary_written": "Backtest summary {output} icine yazildi.",
    "message_operator_workflow_guidance": "Read-only workflow rehberi. Uzun paper operation oncesi readiness ve evidence inceleyin.",
    "message_installing_tui_dependencies": "Ilk calistirma algilandi. Ink dependency'leri {package_manager} ile kuruluyor.",
    "message_node_missing": "Ink control room icin Node package manager gerekir. Rich control room'a dusuluyor.",
    "message_calendar_status_unavailable": "Calendar status gecici olarak kullanilamiyor.\n\n{error}",
    "message_cache_status": "{mode_label}: {mode}\n"
    "{cache_dir_label}: {cache_dir}\n"
    "{snapshot_count_label}: {snapshot_count}",
    "message_market_snapshot_cached": "{symbol} {interval} {lookback} icin {bar_count} bar cache'lendi.\n\n"
    "{cache_dir_label}: {cache_dir}\n{snapshot_count_label}: {snapshot_count}",
    "message_no_tool_news_headlines": "Bu sembol icin tool-driven news headline yok.",
    "message_no_open_positions": "Acik pozisyon yok.",
    "message_no_proposal_candidates": "Henuz proposal candidate kaydi yok.",
    "message_no_trade_proposals": "Henuz trade proposal kaydi yok.",
    "message_finance_operations_unavailable": "Finance operations durumu kullanilamiyor.",
    "message_gross_exposure_above_equity": "Gross exposure equity'nin {limit} uzerinde.",
    "message_idea_presets_execution_policy": "scanner idea'lari proposal olmali ve manuel onay gerektirir",
    "message_idea_score_execution_policy": "score ciktisi yalnizca research icindir; manual review icin proposal-create kullan",
    "message_idea_score_unavailable": "{symbol!r} icin {preset!r} preset'iyle score uretilemedi.",
    "message_largest_position_above_equity": "En buyuk pozisyon equity'nin {limit} uzerinde.",
    "message_background_requires_continuous": "Background modu --continuous gerektirir.",
    "message_launch_plan": "Semboller: {symbols}\nAralik: {interval}\nLookback: {lookback}\n"
    "Surekli: {continuous}\nPoll Saniyesi: {poll_seconds}\nBackground: {background}",
    "message_launch_symbol_required": "En az bir sembol gereklidir.",
    "message_mark_time_unavailable": "mark zamani yok",
    "message_monitor_return_shortcut": "Ctrl+C ile geri don",
    "message_open_position_count_elevated": "Acik pozisyon sayisi yuksek.",
    "message_portfolio_concentration_hhi": "Portfoy konsantrasyon HHI {score:.3f} ile yuksek.",
    "message_position_plan_repair_unavailable": "Position plan repair durumu kullanilamiyor.",
    "message_position_plan_repair_temporarily_unavailable": "Runtime writer veritabaninin sahibiyken position plan repair gecici "
    "olarak kullanilamiyor.\n\n{error}",
    "message_proposal_candidates_temporarily_unavailable": "Runtime writer veritabaninin sahibiyken proposal candidate'leri gecici "
    "olarak kullanilamiyor.\n\n{error}",
    "message_proposal_candidate_created": "{candidate_id} review icin kaydedildi.\n\n"
    "{symbol} {signal} score={score:.2f}",
    "message_proposal_candidate_promoted": "{candidate_id} -> {proposal_id}\n"
    "Pending proposal olarak kuyruga alindi. Broker submission denenmedi.",
    "message_research_cycle_choose_one_action": "--pause, --resume veya --trigger-now icinden yalnizca birini secin.",
    "message_research_cycle_control_status": "{label}: {status}\n{trigger_label}: {trigger_now}",
    "message_research_cycle_reason_requires_action": "--reason icin --pause, --resume veya --trigger-now gerekir.",
    "message_research_cycle_run_summary": "{executed_cycles} evidence-only research cycle calisti.\n"
    "Broker access, proposal approval ve raw web prompt injection kapali kaldi.",
    "message_research_snapshot_recorded": "Snapshot {snapshot_id} research feed icine kaydedildi.",
    "message_observer_api_listening": "Observer API http://{host}:{port} adresinde dinliyor\n\n"
    "Kullanilabilir endpoint'ler:\n{endpoints}",
    "message_observer_api_nonlocal_blocked": "Observer API varsayilan olarak local-only. Loopback host kullanin veya "
    "AGENTIC_TRADER_OBSERVER_API_TOKEN ayarlayip bilincli nonlocal read-only "
    "bind icin --allow-nonlocal gecin.",
    "message_observer_mode_temporarily_unavailable": "Runtime writer veritabaninin sahibiyken {feature} gecici olarak "
    "kullanilamiyor.",
    "message_runtime_gate_open": "Ollama {base_url} adresinde erisilebilir ve {model_name} modeli kullanilabilir.",
    "message_portfolio_temporarily_unavailable": "Runtime writer veritabaninin sahibiyken portfolio view gecici olarak "
    "kullanilamiyor.\n\n{error}",
    "message_preferences_temporarily_unavailable": "Runtime writer veritabaninin sahibiyken preferences gecici olarak "
    "kullanilamiyor.\n\n{error}",
    "message_trade_proposals_temporarily_unavailable": "Runtime writer veritabaninin sahibiyken trade proposal'lari gecici "
    "olarak kullanilamiyor.\n\n{error}",
    "message_trade_proposal_approved": "{proposal_id} -> {status}\norder={order_id} status={outcome_status}",
    "message_trade_proposal_created": "{proposal_id} manual review icin kuyruga alindi.\n\n"
    "{symbol} {side} @ {reference_price:.4f}",
    "message_trade_proposal_reconciled": "{proposal_id} -> {status}\n"
    "order={order_id} status={outcome_status}\n"
    "Broker resubmission denenmedi.",
    "message_trade_proposal_refreshed": "{proposal_id} -> {status}\n"
    "order={order_id} status={outcome_status}\n"
    "Broker resubmission denenmedi.",
    "message_trade_proposal_rejected": "{proposal_id} reddedildi.\n\nNeden: {reason}",
    "message_runtime_mode_transition_allowed": "Runtime mode gecisi {current_mode} -> {target_mode} izinli.",
    "message_runtime_mode_transition_blocked": "Runtime mode gecisi {current_mode} -> {target_mode} bloklandi.",
    "message_setup_bootstrap_guidance": "Interaktif system-tool installer icin `make bootstrap` calistirin.",
    "message_service_stale_runtime_recovered": "Dead PID {pid} artik yasamiyor. Runtime state stopped isaretlendi "
    "ve stale PID temizlendi.",
    "message_service_stale_runtime_recovered_event": "Dead PID {pid} icin stale runtime state kurtarildi.",
    "message_service_stop_requested": "Service PID {pid} runtime control channel uzerinden graceful stop istedi.",
    "message_service_spawned_background": "Service arka planda PID {pid} ile baslatildi.\n\n"
    "Control room responsive kalir. Ilerlemeyi izlemek veya istediginiz an stop "
    "istemek icin live monitor'u acabilirsiniz.",
    "message_stage_update": "[{stage}] {message}",
    "message_stale_runtime_pid": "PID {pid} artik yasamiyor. Sonraki start stale runtime state'i otomatik "
    "kurtaracak.",
    "message_strategy_profile_execution_policy": "profile read-only research metadata'dir; trade execute edemez",
    "message_trading_runtime_blocked": "Ollama ve configured model kullanilabilir olana kadar trading runtime baslamamali.",
    "message_trading_runtime_ready": "Trading runtime tam LLM erisimiyle baslayabilir.",
    "message_training_diagnostic_fallback": "Training modu bu degerlendirmeye deterministic diagnostic fallback ile "
    "devam ediyor cunku LLM gate basarisiz oldu:\n\n{error}",
    "message_tui_missing": "Ink UI dizini bulunamadi. Rich control room'a dusuluyor.",
    "message_unique_artifact_dir_unavailable": "{label} icin unique artifact dizini olusturulamadi",
    "message_waiting_for_last_outcome": "Tamamlanan symbol, exit veya service result bekleniyor.",
    "message_v1_readiness_status_unavailable": "V1 readiness durumu kullanilamiyor.",
}
