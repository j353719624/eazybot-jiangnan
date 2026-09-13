#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
qqmail.py — 个人 QQ 邮箱收发管理 CLI（IMAP + SMTP）
功能对齐 Tencent Agently Mail：list/read/search/send/reply/forward/trash/delete/mark/download/watch
凭据：环境变量 qq_mail（邮箱）/ SMTP_IMAP（授权码），绝不打印。
"""
import os, sys, json, time, argparse, imaplib, email, smtplib, re
from email.header import decode_header, make_header
from email.utils import parseaddr, formataddr, make_msgid, formatdate
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

IMAP_HOST, IMAP_PORT = 'imap.qq.com', 993
SMTP_HOST, SMTP_PORT = 'smtp.qq.com', 465

DIR_MAP = {
    'inbox': 'INBOX',
    'sent': 'Sent Messages',
    'drafts': 'Drafts',
    'trash': 'Deleted Messages',
    'junk': 'Junk',
    'archive': 'Archive',
}

imaplib.Commands['ID'] = ('NONAUTH', 'AUTH', 'SELECTED', 'LOGOUT')


def fail(msg, code=2, **extra):
    print(json.dumps({'ok': False, 'error': msg, **extra}, ensure_ascii=False))
    sys.exit(code)


def emit(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=1))


def creds():
    user, pwd = (os.environ.get('qq_mail') or os.environ.get('QQ_MAIL'),
                 os.environ.get('SMTP_IMAP') or os.environ.get('QQ_MAIL_AUTH'))
    if not user or not pwd:
        fail('缺少凭据：请设置环境变量 QQ_MAIL（邮箱地址）与 QQ_MAIL_AUTH（SMTP/IMAP 授权码），'
             '或用 --account/--auth-code/--config 注入', 2)
    return user, pwd


def connect():
    user, pwd = creds()
    M = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    M._simple_command('ID', '("name" "qq-mail-skill" "version" "1.0.0")')
    try:
        M.login(user, pwd)
    except imaplib.IMAP4.error as e:
        fail(f'IMAP 登录失败：{e}（授权码可能失效，请用户重新生成）', 3)
    return M, user, pwd


def dec(s):
    if s is None:
        return ''
    if isinstance(s, bytes):
        s = s.decode('utf-8', 'replace')
    s = re.sub(r'\r?\n[ \t]+', ' ', s)  # unfold 折行头，否则 decode_header 失效
    try:
        return str(make_header(decode_header(s)))
    except Exception:
        return s


def resolve_dir(name):
    return DIR_MAP.get((name or 'inbox').lower(), name or 'INBOX')


def imap_date(s):
    return datetime.strptime(s, '%Y-%m-%d').strftime('%d-%b-%Y')


def parse_date_hdr(s):
    try:
        dt = email.utils.parsedate_to_datetime(s)
        from datetime import timezone, timedelta
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M')
    except Exception:
        return s or ''


def walk_parts(msg):
    texts, htmls, atts = [], [], []
    for part in msg.walk():
        if part.is_multipart():
            continue
        cd = str(part.get('Content-Disposition') or '')
        ctype = part.get_content_type()
        filename = part.get_filename()
        if filename:
            filename = dec(filename)
        if ('attachment' in cd.lower()) or filename:
            payload = part.get_payload(decode=True) or b''
            atts.append({'att_index': len(atts) + 1, 'filename': filename or f'unnamed-{len(atts)+1}',
                         'content_type': ctype, 'size': len(payload)})
        elif ctype in ('text/plain', 'text/html'):
            payload = part.get_payload(decode=True) or b''
            charset = part.get_content_charset() or 'utf-8'
            try:
                txt = payload.decode(charset, 'replace')
            except LookupError:
                txt = payload.decode('utf-8', 'replace')
            (texts if ctype == 'text/plain' else htmls).append(txt)
    return texts, htmls, atts


def scan(M, folder, since=None, before=None, unseen=None, max_scan=300):
    typ, _ = M.select(f'"{folder}"')
    if typ != 'OK':
        return []
    crit = []
    if since:
        crit += ['SINCE', imap_date(since)]
    if before:
        crit += ['BEFORE', imap_date(before)]
    if unseen:
        crit += ['UNSEEN']
    typ, data = M.uid('SEARCH', *(crit or ['ALL']))
    if typ != 'OK':
        return []
    uids = data[0].split()[::-1][:max_scan]
    out = []
    for u in uids:
        typ, d = M.uid('FETCH', u, '(FLAGS BODYSTRUCTURE BODY.PEEK[HEADER])')
        if typ != 'OK' or not d or d[0] is None or not isinstance(d[0], tuple):
            continue
        meta, hdr = d[0][0], d[0][1]
        meta_s = meta.decode('utf-8', 'replace') if isinstance(meta, bytes) else str(meta)
        fm = re.search(r'FLAGS \(([^)]*)\)', meta_s)
        flags = fm.group(1).encode() if fm else b''
        out.append((u, flags, None, hdr, meta_s.encode()))
    return out


def local_filter(items, q=None, frm=None, to=None, has_att=None, search_in='all'):
    res = []
    q_l = (q or '').lower()
    frm_l, to_l = (frm or '').lower(), (to or '').lower()
    for (uid, flags, idate, hdr, bs) in items:
        b = msg_brief(uid, flags, hdr, bs)
        if q_l:
            hay = {'subject': b['subject'].lower(), 'from': b['from'].lower(), 'to': b['to'].lower()}
            target = hay.get(search_in if search_in != 'all' else 'subject', '')
            if search_in != 'content' and q_l not in target:
                continue
            if search_in == 'all' and q_l not in (b['subject'] + ' ' + b['from'] + ' ' + b['to']).lower():
                continue
            # content 搜索由 cmd_search 读正文后处理
        if frm_l and frm_l not in b['from'].lower():
            continue
        if to_l and to_l not in b['to'].lower():
            continue
        if has_att is True and not b['has_attachments']:
            continue
        if has_att is False and b['has_attachments']:
            continue
        res.append(b)
    return res


def msg_brief(uid, flags, hdr_bytes, bs_meta=''):
    if isinstance(bs_meta, bytes):
        bs_meta = bs_meta.decode('utf-8', 'replace')
    msg = email.message_from_bytes(hdr_bytes)
    seen = '\\Seen' in (flags or b'').decode('utf-8', 'replace')
    has_att = ('ATTACHMENT' in bs_meta.upper()) or ('NAME="' in bs_meta.upper())
    return {
        'uid': uid.decode() if isinstance(uid, bytes) else uid,
        'subject': dec(msg.get('Subject')),
        'from': dec(msg.get('From')),
        'to': dec(msg.get('To')),
        'date': parse_date_hdr(msg.get('Date')),
        'is_read': seen,
        'has_attachments': has_att,
    }


def paginate(items, limit, cursor):
    cursor = int(cursor or 0)
    page = items[cursor:cursor + int(limit)]
    nxt = cursor + int(limit) if cursor + int(limit) < len(items) else None
    return page, nxt, len(items)


def cmd_folders(a):
    M, _, _ = connect()
    typ, data = M.list()
    folders = []
    for line in data:
        s = line.decode('utf-8', 'replace')
        m = re.search(r'(?:^|\s)"([^"]+)"\s*$', s) or re.search(r'\s([^\s"]+)$', s)
        name = m.group(1) if m else s
        label = {v: k for k, v in DIR_MAP.items()}.get(name, name)
        folders.append({'dir': label, 'path': name})
    M.logout()
    emit({'ok': True, 'folders': folders})


def cmd_list(a):
    M, _, _ = connect()
    folder = resolve_dir(a.dir)
    items = scan(M, folder, since=a.after, before=a.before, unseen=a.is_unread, max_scan=a.max_scan)
    M.logout()
    res = local_filter(items, has_att=a.has_attachments)
    page, nxt, total = paginate(res, a.limit, a.cursor)
    emit({'ok': True, 'dir': a.dir or 'inbox', 'total_matched': total,
          'next_cursor': nxt, 'messages': page})


def cmd_search(a):
    M, _, _ = connect()
    folder = resolve_dir(a.dir)
    items = scan(M, folder, since=a.after, before=a.before, unseen=a.is_unread, max_scan=a.max_scan)
    res = local_filter(items, frm=a.from_, to=a.to, has_att=a.has_attachments)
    if a.q:
        q_l = a.q.lower()
        hits = []
        need_body = []
        for b in res:
            if a.search_in == 'content':
                need_body.append(b)
            elif a.search_in == 'subject' and q_l in b['subject'].lower():
                hits.append(b)
            elif a.search_in == 'from' and q_l in b['from'].lower():
                hits.append(b)
            elif a.search_in == 'to' and q_l in b['to'].lower():
                hits.append(b)
            elif a.search_in == 'all' and q_l in (b['subject'] + ' ' + b['from'] + ' ' + b['to']).lower():
                hits.append(b)
        if a.search_in == 'content':
            M.select(f'"{folder}"')
            for b in res[:60]:
                typ, dd = M.uid('FETCH', b['uid'], '(BODY.PEEK[])')
                if dd and dd[0] and isinstance(dd[0], tuple):
                    full = email.message_from_bytes(dd[0][1])
                    texts, htmls, _ = walk_parts(full)
                    if q_l in '\n'.join(texts + htmls).lower():
                        hits.append(b)
        res = hits
    M.logout()
    page, nxt, total = paginate(res, a.limit, a.cursor)
    emit({'ok': True, 'query': a.q, 'total_matched': total, 'next_cursor': nxt, 'messages': page})


def _fetch_full(M, folder, uid):
    typ, _ = M.select(f'"{folder}"')
    if typ != 'OK':
        fail(f'无法打开文件夹 {folder}', 2)
    typ, d = M.uid('FETCH', uid, '(FLAGS BODY.PEEK[])')
    if typ != 'OK' or not d or not d[0] or not isinstance(d[0], tuple):
        fail(f'邮件 uid={uid} 不存在或读取失败', 2)
    fm = re.search(r'FLAGS \(([^)]*)\)', d[0][0].decode('utf-8', 'replace'))
    flags = fm.group(1) if fm else ''
    return email.message_from_bytes(d[0][1]), flags


def cmd_read(a):
    M, _, _ = connect()
    folder = resolve_dir(a.dir)
    msg, flags = _fetch_full(M, folder, a.id)
    texts, htmls, atts = walk_parts(msg)
    M.logout()
    emit({
        'ok': True, 'dir': a.dir or 'inbox', 'uid': a.id,
        'message_id': msg.get('Message-ID'),
        'subject': dec(msg.get('Subject')),
        'from': dec(msg.get('From')), 'to': dec(msg.get('To')), 'cc': dec(msg.get('Cc')),
        'date': parse_date_hdr(msg.get('Date')),
        'body_text': '\n'.join(texts) if texts else None,
        'body_html': '\n'.join(htmls) if htmls else None,
        'attachments': atts,
    })


def cmd_download(a):
    M, _, _ = connect()
    folder = resolve_dir(a.dir)
    msg, _ = _fetch_full(M, folder, a.msg)
    M.logout()
    outdir = os.path.abspath(os.path.expanduser(a.output or '.'))
    os.makedirs(outdir, exist_ok=True)
    atts = []
    for part in msg.walk():
        if part.is_multipart():
            continue
        fn = part.get_filename()
        cd = str(part.get('Content-Disposition') or '')
        if (fn or 'attachment' in cd.lower()):
            payload = part.get_payload(decode=True)
            if payload is None:
                continue
            atts.append((dec(fn) if fn else f'unnamed-{len(atts)+1}', payload))
    if not atts:
        fail('未找到附件', 2)
    target = None
    if str(a.att).isdigit():
        i = int(a.att) - 1
        if 0 <= i < len(atts):
            target = atts[i]
    if target is None:
        for fname, payload in atts:
            if fname == a.att or a.att in fname:
                target = (fname, payload)
                break
    if target is None:
        fail(f'附件 {a.att} 不存在；现有：{[x[0] for x in atts]}', 2)
    fname, payload = target
    path = os.path.join(outdir, fname)
    n = 1
    base, ext = os.path.splitext(path)
    while os.path.exists(path):
        path = f'{base}({n}){ext}'
        n += 1
    with open(path, 'wb') as f:
        f.write(payload)
    emit({'ok': True, 'saved_to': path, 'size': len(payload)})


def _build_msg(from_addr, to_list, subject, body, html, cc_list, bcc_list, atts, reply_to=None):
    m = MIMEMultipart()
    m['From'] = from_addr
    m['To'] = ', '.join(to_list)
    if cc_list:
        m['Cc'] = ', '.join(cc_list)
    if bcc_list:
        m['Bcc'] = ', '.join(bcc_list)
    m['Subject'] = subject
    m['Date'] = formatdate(localtime=True)
    m['Message-ID'] = make_msgid(domain=from_addr.split('@')[-1])
    if reply_to:
        mid, refs = reply_to
        m['In-Reply-To'] = mid
        m['References'] = refs or mid
    m.attach(MIMEText(body, 'html' if html else 'plain', 'utf-8'))
    for pth in atts:
        with open(pth, 'rb') as f:
            part = MIMEApplication(f.read())
        part.add_header('Content-Disposition', 'attachment', filename=os.path.basename(pth))
        m.attach(part)
    return m


def _send_flow(a, build_fn):
    all_rcpts = list(a.to or []) + list(a.cc or []) + list(a.bcc or [])
    if not all_rcpts:
        fail('缺少收件人 --to', 2)
    body, html = a.body, getattr(a, 'html', False)
    if getattr(a, 'body_file', None):
        with open(a.body_file, encoding='utf-8') as f:
            body = f.read()
        if not html:
            head = body[:300].lower()
            html = ('<html' in head) or ('<body' in head) or ('<p>' in head) or ('<br' in head)
    if not getattr(a, 'subject', None):
        fail('缺少 --subject', 2)
    summary = {'action': getattr(a, 'action', 'send'), 'to': list(a.to or []),
               'cc': list(a.cc or []), 'bcc': list(a.bcc or []), 'subject': a.subject,
               'attachments': list(a.attachment or []), 'body_preview': (body or '')[:200]}
    if not a.confirm:
        emit({'ok': False, 'stage': 'confirm_required', 'summary': summary,
              'hint': '确认无误后加 --confirm 重新执行以发送'})
        sys.exit(8)
    user, pwd = creds()
    msg = build_fn(user)
    try:
        S = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30)
        S.login(user, pwd)
        S.sendmail(user, all_rcpts, msg.as_bytes())
        S.quit()
    except smtplib.SMTPException as e:
        fail(f'SMTP 发送失败：{e}', 1)
    note = '已发送'
    try:
        M2 = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        M2._simple_command('ID', '("name" "qq-mail-skill" "version" "1.0.0")')
        M2.login(user, pwd)
        M2.append('"Sent Messages"', '\\Seen', imaplib.Time2Internaldate(time.time()), msg.as_bytes())
        M2.logout()
        note = '已发送，并同步到「已发送」文件夹'
    except Exception:
        note = '已发送（同步到已发送文件夹失败，不影响发送）'
    emit({'ok': True, 'sent': True, 'summary': summary, 'note': note})


def cmd_send(a):
    a.action = 'send'
    _send_flow(a, lambda user: _build_msg(
        user, list(a.to), a.subject, a.body, a.html,
        list(a.cc or []), list(a.bcc or []), list(a.attachment or [])))


def _get_orig(a):
    M, _, _ = connect()
    folder = resolve_dir(a.dir)
    msg, _ = _fetch_full(M, folder, a.id)
    M.logout()
    return msg


def cmd_reply(a):
    a.action = 'reply'
    orig = _get_orig(a)
    orig_mid = orig.get('Message-ID') or ''
    orig_refs = orig.get('References') or ''
    addr = lambda h: [parseaddr(dec(x))[1] for x in (h or '').split(',') if parseaddr(dec(x))[1]]
    orig_from = addr(orig.get('From'))
    orig_from = orig_from[0] if orig_from else ''
    orig_to, orig_cc = addr(orig.get('To')), addr(orig.get('Cc'))
    subject = dec(orig.get('Subject'))
    if not subject.lower().startswith('re:'):
        subject = 'Re: ' + subject
    a.subject = getattr(a, 'subject', None) or subject  # reply 未指定主题时沿用 Re: 原主题

    def build(user):
        if a.reply_all:
            to_list = [orig_from] + [t for t in orig_to if t != user]
            cc_list = list(a.cc or []) + [c for c in orig_cc if c != user]
        else:
            to_list, cc_list = [orig_from], list(a.cc or [])
        to_list += [t for t in (a.to or []) if t not in to_list]
        a.to, a.cc = to_list, cc_list  # 让 _send_flow 的确认 summary 和收件人校验生效
        return _build_msg(user, to_list, subject, a.body, a.html, cc_list,
                          list(a.bcc or []), list(a.attachment or []),
                          reply_to=(orig_mid, orig_refs))
    # 提前解析收件人，供确认摘要展示（reply 可不带 --to）
    user, _ = creds()
    if a.reply_all:
        to_list = [orig_from] + [t for t in orig_to if t != user]
    else:
        to_list = [orig_from]
    a.to = to_list + [t for t in (a.to or []) if t not in to_list]
    _send_flow(a, build)


def cmd_forward(a):
    a.action = 'forward'
    orig = _get_orig(a)
    subject = dec(orig.get('Subject'))
    if not subject.lower().startswith(('fwd:', 'fw:')):
        subject = 'Fwd: ' + subject

    def build(user):
        atts = list(a.attachment or [])
        if a.include_attachments:
            import tempfile
            for part in orig.walk():
                if part.is_multipart():
                    continue
                fn = part.get_filename()
                cd = str(part.get('Content-Disposition') or '')
                if fn or 'attachment' in cd.lower():
                    payload = part.get_payload(decode=True)
                    if payload is None:
                        continue
                    fn = dec(fn) if fn else f'unnamed-{len(atts)+1}'
                    tmp = os.path.join(tempfile.gettempdir(), fn)
                    with open(tmp, 'wb') as f:
                        f.write(payload)
                    atts.append(tmp)
        hdr = ("---------- 转发邮件 ----------\n"
               f"发件人: {dec(orig.get('From'))}\n"
               f"日期: {parse_date_hdr(orig.get('Date'))}\n"
               f"主题: {dec(orig.get('Subject'))}\n\n")
        texts, htmls, _ = walk_parts(orig)
        orig_body = '\n'.join(texts or htmls)[:5000]
        full = (hdr + orig_body + '\n\n' + (a.body or '')) if a.body else (hdr + orig_body)
        return _build_msg(user, list(a.to), subject, full, False,
                          list(a.cc or []), list(a.bcc or []), atts)
    _send_flow(a, build)


def cmd_trash(a):
    if not a.confirm:
        emit({'ok': False, 'stage': 'confirm_required',
              'summary': {'action': 'trash', 'uid': a.id, 'dir': a.dir},
              'hint': '确认后加 --confirm 执行'})
        sys.exit(8)
    M, _, _ = connect()
    folder = resolve_dir(a.dir)
    M.select(f'"{folder}"')
    typ, _ = M.uid('COPY', a.id, '"Deleted Messages"')
    if typ != 'OK':
        fail(f'复制到回收站失败 uid={a.id}', 2)
    M.uid('STORE', a.id, '+FLAGS', '(\\Deleted)')
    M.expunge()
    M.logout()
    emit({'ok': True, 'trashed': a.id, 'note': '已移到回收站'})


def cmd_delete(a):
    if not a.confirm:
        emit({'ok': False, 'stage': 'confirm_required',
              'summary': {'action': 'delete', 'uid': a.id, 'all': a.all},
              'hint': '永久删除不可恢复，确认后加 --confirm 执行'})
        sys.exit(8)
    M, _, _ = connect()
    typ, _ = M.select('"Deleted Messages"')
    if typ != 'OK':
        fail('无法打开回收站', 2)
    if a.all:
        typ, d = M.uid('SEARCH', 'ALL')
        uids = d[0].split()
        for u in uids:
            M.uid('STORE', u, '+FLAGS', '(\\Deleted)')
        M.expunge()
        n = len(uids)
    else:
        if not a.id:
            fail('--id 或 --all 必填一个', 2)
        M.uid('STORE', a.id, '+FLAGS', '(\\Deleted)')
        M.expunge()
        n = 1
    M.logout()
    emit({'ok': True, 'deleted_count': n})


def cmd_mark(a):
    M, _, _ = connect()
    folder = resolve_dir(a.dir)
    M.select(f'"{folder}"')
    if a.read:
        M.uid('STORE', a.id, '+FLAGS', '(\\Seen)')
        marked = 'read'
    else:
        M.uid('STORE', a.id, '-FLAGS', '(\\Seen)')
        marked = 'unread'
    M.logout()
    emit({'ok': True, 'uid': a.id, 'marked': marked})


def cmd_watch(a):
    user, pwd = creds()
    seen_ids = set()
    deadline = time.time() + a.duration
    print(f'# watching INBOX, interval={a.interval}s, duration={a.duration}s', flush=True)
    while time.time() < deadline:
        try:
            M = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
            M._simple_command('ID', '("name" "qq-mail-skill" "version" "1.0.0")')
            M.login(user, pwd)
            M.select('INBOX')
            typ, d = M.uid('SEARCH', 'UNSEEN')
            for u in d[0].split():
                if u in seen_ids:
                    continue
                seen_ids.add(u)
                typ, dd = M.uid('FETCH', u, '(BODY.PEEK[])')
                if dd and dd[0] and isinstance(dd[0], tuple):
                    msg = email.message_from_bytes(dd[0][1])
                    texts, htmls, atts = walk_parts(msg)
                    print(json.dumps({
                        'new_mail': True, 'uid': u.decode(),
                        'from': dec(msg.get('From')), 'subject': dec(msg.get('Subject')),
                        'date': parse_date_hdr(msg.get('Date')),
                        'body_preview': '\n'.join(texts or htmls)[:300],
                        'attachments': [x['filename'] for x in atts],
                    }, ensure_ascii=False), flush=True)
            M.logout()
        except Exception as e:
            print(json.dumps({'watch_error': str(e)}, ensure_ascii=False), flush=True)
        time.sleep(a.interval)
    emit({'ok': True, 'note': f'watch 结束，共发现新邮件 {len(seen_ids)} 封'})


def main():
    # 凭据注入：全局参数 --account/--auth-code/--config（也可用环境变量）
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument('--account', help='QQ 邮箱地址（默认读环境变量 QQ_MAIL）')
    pre.add_argument('--auth-code', help='SMTP/IMAP 授权码（默认读环境变量 QQ_MAIL_AUTH）')
    pre.add_argument('--config', help='凭据 JSON 文件路径（{"account":..., "auth_code":...}，权限建议 600）')
    p = argparse.ArgumentParser(description='个人 QQ 邮箱 CLI（IMAP/SMTP）', parents=[pre])
    a_pre, _ = pre.parse_known_args()
    cfg_path = a_pre.config or os.path.expanduser('~/.qq-mail/config.json')
    if a_pre.config or not ((os.environ.get('qq_mail') or os.environ.get('QQ_MAIL'))
                            and (os.environ.get('SMTP_IMAP') or os.environ.get('QQ_MAIL_AUTH'))):
        try:
            with open(cfg_path, encoding='utf-8') as f:
                cfg = json.load(f)
            os.environ.setdefault('QQ_MAIL', cfg.get('account', ''))
            os.environ.setdefault('QQ_MAIL_AUTH', cfg.get('auth_code', ''))
        except FileNotFoundError:
            pass
    if a_pre.account:
        os.environ['QQ_MAIL'] = a_pre.account
    if a_pre.auth_code:
        os.environ['QQ_MAIL_AUTH'] = a_pre.auth_code
    sub = p.add_subparsers(dest='cmd', required=True)

    sub.add_parser('folders').set_defaults(fn=cmd_folders)

    sp = sub.add_parser('list')
    sp.add_argument('--dir', default='inbox')
    sp.add_argument('--limit', type=int, default=10)
    sp.add_argument('--cursor', default=None)
    sp.add_argument('--after', help='YYYY-MM-DD')
    sp.add_argument('--before', help='YYYY-MM-DD')
    sp.add_argument('--has-attachments', action='store_true')
    sp.add_argument('--is-unread', action='store_true')
    sp.add_argument('--max-scan', type=int, default=300)
    sp.set_defaults(fn=cmd_list)

    sp = sub.add_parser('search')
    sp.add_argument('--q')
    sp.add_argument('--search-in', default='all', choices=['all', 'subject', 'content', 'from', 'to'])
    sp.add_argument('--from', dest='from_')
    sp.add_argument('--to')
    sp.add_argument('--dir', default='inbox')
    sp.add_argument('--limit', type=int, default=10)
    sp.add_argument('--cursor', default=None)
    sp.add_argument('--after')
    sp.add_argument('--before')
    sp.add_argument('--has-attachments', action='store_true')
    sp.add_argument('--is-unread', action='store_true')
    sp.add_argument('--max-scan', type=int, default=300)
    sp.set_defaults(fn=cmd_search)

    sp = sub.add_parser('read')
    sp.add_argument('--id', required=True)
    sp.add_argument('--dir', default='inbox')
    sp.set_defaults(fn=cmd_read)

    sp = sub.add_parser('download')
    sp.add_argument('--msg', required=True)
    sp.add_argument('--att', required=True)
    sp.add_argument('--output', default='.')
    sp.add_argument('--dir', default='inbox')
    sp.set_defaults(fn=cmd_download)

    sp = sub.add_parser('send')
    sp.add_argument('--to', action='append', required=True)
    sp.add_argument('--cc', action='append')
    sp.add_argument('--bcc', action='append')
    sp.add_argument('--subject', required=True)
    sp.add_argument('--body')
    sp.add_argument('--body-file')
    sp.add_argument('--html', action='store_true')
    sp.add_argument('--attachment', action='append')
    sp.add_argument('--confirm', action='store_true')
    sp.set_defaults(fn=cmd_send)

    sp = sub.add_parser('reply')
    sp.add_argument('--id', required=True)
    sp.add_argument('--dir', default='inbox')
    sp.add_argument('--body')
    sp.add_argument('--body-file')
    sp.add_argument('--html', action='store_true')
    sp.add_argument('--reply-all', action='store_true')
    sp.add_argument('--to', action='append')
    sp.add_argument('--cc', action='append')
    sp.add_argument('--bcc', action='append')
    sp.add_argument('--attachment', action='append')
    sp.add_argument('--confirm', action='store_true')
    sp.set_defaults(fn=cmd_reply)

    sp = sub.add_parser('forward')
    sp.add_argument('--id', required=True)
    sp.add_argument('--dir', default='inbox')
    sp.add_argument('--to', action='append', required=True)
    sp.add_argument('--cc', action='append')
    sp.add_argument('--bcc', action='append')
    sp.add_argument('--body')
    sp.add_argument('--body-file')
    sp.add_argument('--html', action='store_true')
    sp.add_argument('--include-attachments', action='store_true')
    sp.add_argument('--attachment', action='append')
    sp.add_argument('--confirm', action='store_true')
    sp.set_defaults(fn=cmd_forward)

    sp = sub.add_parser('trash')
    sp.add_argument('--id', required=True)
    sp.add_argument('--dir', default='inbox')
    sp.add_argument('--confirm', action='store_true')
    sp.set_defaults(fn=cmd_trash)

    sp = sub.add_parser('delete')
    sp.add_argument('--id')
    sp.add_argument('--all', action='store_true')
    sp.add_argument('--confirm', action='store_true')
    sp.set_defaults(fn=cmd_delete)

    sp = sub.add_parser('mark')
    sp.add_argument('--id', required=True)
    sp.add_argument('--dir', default='inbox')
    g = sp.add_mutually_exclusive_group(required=True)
    g.add_argument('--read', action='store_true')
    g.add_argument('--unread', dest='read', action='store_false')
    sp.set_defaults(fn=cmd_mark, read=True)

    sp = sub.add_parser('watch')
    sp.add_argument('--interval', type=int, default=30)
    sp.add_argument('--duration', type=int, default=600)
    sp.set_defaults(fn=cmd_watch)

    a = p.parse_args()
    a.fn(a)


if __name__ == '__main__':
    main()
