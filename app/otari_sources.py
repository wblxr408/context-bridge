"""Bounded public HTTPS retrieval on explicitly approved exact domains."""
from html.parser import HTMLParser
import http.client
import ipaddress
import socket
import ssl
from urllib.parse import urlsplit


class SourceError(ValueError):
    pass


def approved_url(url, domains):
    try:
        parts = urlsplit(url)
        host = (parts.hostname or '').encode('idna').decode('ascii').lower()
        allowed = {str(d).encode('idna').decode('ascii').lower() for d in domains}
        if parts.scheme != 'https' or host not in allowed or parts.username or parts.password or parts.port not in (None, 443):
            raise SourceError('Only approved HTTPS domains may be fetched')
        return parts
    except (ValueError, UnicodeError):
        raise SourceError('Invalid or unapproved source URL') from None


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip, self.parts = 0, []

    def handle_starttag(self, tag, attrs):
        if tag in {'script', 'style', 'noscript', 'svg'}:
            self.skip += 1
        elif tag in {'p', 'div', 'br', 'li', 'h1', 'h2', 'h3', 'tr', 'pre'} and not self.skip:
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in {'script', 'style', 'noscript', 'svg'} and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def fetch_public_source(url):
    """Pin a public address; no redirects, proxy, credentials or cookies."""
    try:
        parsed = urlsplit(url)
        host = parsed.hostname
        if parsed.scheme != 'https' or not host or parsed.username or parsed.password or parsed.port not in (None, 443):
            raise SourceError('Only public HTTPS sources are supported')
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
            raise SourceError('Source must resolve only to public addresses')
        pinned = addresses[0][4][0]

        class PinnedHTTPS(http.client.HTTPSConnection):
            def connect(self):
                self.sock = self._context.wrap_socket(socket.create_connection((pinned, 443), self.timeout), server_hostname=host)

        connection = PinnedHTTPS(host, timeout=15, context=ssl.create_default_context())
        try:
            connection.request('GET', (parsed.path or '/') + ('?' + parsed.query if parsed.query else ''), headers={
                'User-Agent': 'ContextBridge-Contest/1.0', 'Accept': 'text/html,text/plain,text/markdown', 'Accept-Encoding': 'identity'})
            response = connection.getresponse()
            content_type = response.getheader('Content-Type', '').split(';')[0].lower()
            if response.status != 200 or content_type not in {'text/html', 'text/plain', 'text/markdown'}:
                raise SourceError('Source did not return supported text; redirects are not followed')
            raw = response.read(512 * 1024 + 1)
            if len(raw) > 512 * 1024 or response.getheader('Content-Encoding', 'identity') != 'identity':
                raise SourceError('Source exceeds text limits')
            text = raw.decode('utf-8', errors='replace')
            if content_type == 'text/html':
                parser = _Text()
                parser.feed(text)
                text = '\n'.join(line.strip() for line in ''.join(parser.parts).splitlines() if line.strip())
            if not text.strip():
                raise SourceError('Source has no readable text')
            return {'url': url, 'title': host + (parsed.path or '/'), 'text': text[:60000]}
        finally:
            connection.close()
    except (OSError, http.client.HTTPException, ValueError) as exc:
        raise SourceError('Public source could not be materialized') from exc
