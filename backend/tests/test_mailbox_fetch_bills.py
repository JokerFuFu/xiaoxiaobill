import services.mailbox as mailbox


class _DummyImap:
    def __init__(self, search_uids, header_map):
        self._search_uids = search_uids
        self._header_map = header_map

    def select(self, *a, **k):
        return ('OK', [b'1'])

    def uid(self, cmd, *args):
        if cmd == 'SEARCH':
            return ('OK', [self._search_uids])
        if cmd == 'FETCH':
            mail_uid_arg = args[0]
            query = args[1] if len(args) > 1 else ''
            if 'HEADER.FIELDS' in query:
                resp = []
                for one in mail_uid_arg.split(b','):
                    hdr = self._header_map.get(one)
                    if hdr is not None:
                        resp.append((b'%s (UID %s BODY[HEADER.FIELDS] {%d}' % (one, one, len(hdr)), hdr))
                return ('OK', resp)
            return ('OK', [(b'', b'')])
        raise AssertionError(f'unexpected uid() call: {cmd} {args}')

    def logout(self):
        pass


def test_fetch_bills_marks_needs_password_for_pending_attachment(mail_uid, monkeypatch):
    uid = mail_uid
    mailbox.save_config(uid, host='imap.qq.com', port=993, address='a@qq.com', auth_code='code')

    header = b'Subject: Test\r\nFrom: alipay@alipay.com\r\nDate: Mon, 1 Jun 2026 08:00:00 +0800\r\n\r\n'
    dummy = _DummyImap(search_uids=b'100', header_map={b'100': header})
    monkeypatch.setattr(mailbox, '_connect', lambda cfg: dummy)
    monkeypatch.setattr(mailbox, '_fetch_msg', lambda M, mail_uid: object())
    monkeypatch.setattr(mailbox, '_iter_attachments', lambda msg: [
        (0, 'bill.zip', 1000, object()),
        (1, 'other.csv', 200, object()),
    ])

    mailbox._mark_pending(uid, '100', {'subject': 's', 'sender': 'x', 'date': 'd'},
                          {'index': 0, 'filename': 'bill.zip'})

    mails = mailbox.fetch_bills(uid, days=90)

    assert len(mails) == 1
    atts = {a['index']: a for a in mails[0]['attachments']}
    assert atts[0]['needs_password'] is True
    assert atts[1]['needs_password'] is False
