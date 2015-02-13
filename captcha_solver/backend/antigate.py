from tempfile import mkstemp
from base64 import b64encode
try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode
from urlparse import urljoin


from captcha_solver.backend.base import CaptchaBackend
from captcha_solver import (CaptchaServiceError, ServiceTooBusy,
                                BalanceTooLow, SolutionNotReady)


class AntigateBackend(CaptchaBackend):
    def setup(self, api_key, service_url='http://antigate.com', **kwargs):
        super(AntigateBackend, self).setup(**kwargs)
        self.api_key = api_key
        self.service_url = service_url

    def get_submit_captcha_request(self, data, **kwargs):
        t = self.Transport()
        post = {
            'key': self.api_key,
            'method': 'base64',
            'body': b64encode(data),
        }
        post.update(kwargs)
        t.setup(post=post)
        url = urljoin(self.service_url, 'in.php')
        t.setup(url=url)
        return t

    def parse_submit_captcha_response(self, res):
        if res.code == 200:
            if res.body.startswith('OK|'):
                return res.body.split('|', 1)[1]
            elif res.body == 'ERROR_NO_SLOT_AVAILABLE':
                raise ServiceTooBusy('Service too busy')
            elif res.body == 'ERROR_ZERO_BALANCE':
                raise BalanceTooLow('Balance too low')
            else:
                raise CaptchaServiceError(res.body)
        else:
            raise CaptchaServiceError('Returned HTTP code: %d' % res.code)
        
    def get_check_solution_request(self, captcha_id):
        params = {'key': self.api_key, 'action': 'get', 'id': captcha_id}
        url = urljoin(self.service_url, 'res.php?%s' % urlencode(params))
        t = self.Transport()
        t.setup(url=url)
        return t

    def parse_check_solution_response(self, res):
        if res.code == 200:
            if res.body.startswith('OK|'):
                return res.body.split('|', 1)[1]
            elif res.body == 'CAPCHA_NOT_READY':
                raise SolutionNotReady('Solution not ready')
            else:
                raise CaptchaServiceError(res.body)
        else:
            raise CaptchaServiceError('Returned HTTP code: %d' % res.code)
