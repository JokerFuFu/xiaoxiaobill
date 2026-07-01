import services.mailbox as mailbox


def test_mark_and_load_pending(mail_uid):
    uid = mail_uid
    mailbox._mark_pending(uid, '100', {'subject': 's', 'sender': 'x', 'date': 'd'},
                          {'index': 0, 'filename': 'bill.zip'})
    pending = mailbox._load_pending(uid)
    assert pending['100']['indices'] == [0]
    assert pending['100']['attachments'] == [{'index': 0, 'filename': 'bill.zip'}]
    assert mailbox.pending_count(uid) == 1


def test_mark_pending_twice_same_index_does_not_duplicate(mail_uid):
    uid = mail_uid
    att = {'index': 0, 'filename': 'bill.zip'}
    meta = {'subject': 's', 'sender': 'x', 'date': 'd'}
    mailbox._mark_pending(uid, '100', meta, att)
    mailbox._mark_pending(uid, '100', meta, att)
    pending = mailbox._load_pending(uid)
    assert pending['100']['indices'] == [0]
    assert len(pending['100']['attachments']) == 1


def test_clear_pending_index_removes_entry_when_empty(mail_uid):
    uid = mail_uid
    mailbox._mark_pending(uid, '200', {'subject': 's', 'sender': 'x', 'date': 'd'},
                          {'index': 1, 'filename': 'a.zip'})
    assert mailbox.pending_count(uid) == 1
    mailbox._clear_pending_index(uid, '200', 1)
    assert mailbox.pending_count(uid) == 0
    assert mailbox._load_pending(uid) == {}


def test_clear_pending_index_keeps_other_indices(mail_uid):
    uid = mail_uid
    meta = {'subject': 's', 'sender': 'x', 'date': 'd'}
    mailbox._mark_pending(uid, '300', meta, {'index': 0, 'filename': 'a.zip'})
    mailbox._mark_pending(uid, '300', meta, {'index': 1, 'filename': 'b.zip'})
    mailbox._clear_pending_index(uid, '300', 0)
    pending = mailbox._load_pending(uid)
    assert pending['300']['indices'] == [1]


def test_save_pending_keeps_newest_500(mail_uid):
    uid = mail_uid
    data = {
        str(i): {'subject': 's', 'sender': 'x', 'date': 'd', 'indices': [0],
                 'attachments': [{'index': 0, 'filename': 'a.zip'}], 'seen_at': f'{i:05d}'}
        for i in range(510)
    }
    mailbox._save_pending(uid, data)
    loaded = mailbox._load_pending(uid)
    assert len(loaded) == 500
    assert set(loaded.keys()) == {str(i) for i in range(10, 510)}


def test_save_and_load_auto_status_records_error(mail_uid):
    uid = mail_uid
    mailbox._save_auto_status(uid, ok=False, error='登录失败:授权码可能已过期')
    status = mailbox._load_auto_status(uid)
    assert status['last_error'] == '登录失败:授权码可能已过期'
    assert status.get('last_success_at', '') == ''
    assert status['last_run_at']


def test_save_auto_status_success_clears_error(mail_uid):
    uid = mail_uid
    mailbox._save_auto_status(uid, ok=False, error='上一次失败')
    mailbox._save_auto_status(uid, ok=True)
    status = mailbox._load_auto_status(uid)
    assert status['last_error'] == ''
    assert status['last_success_at']
