import services.mailbox as mailbox


def test_should_start_scheduler_in_production_single_process():
    assert mailbox.should_start_mail_scheduler(debug=False, werkzeug_run_main=None) is True


def test_should_start_scheduler_debug_parent_process_skips():
    assert mailbox.should_start_mail_scheduler(debug=True, werkzeug_run_main=None) is False


def test_should_start_scheduler_debug_reloader_child_starts():
    assert mailbox.should_start_mail_scheduler(debug=True, werkzeug_run_main='true') is True
