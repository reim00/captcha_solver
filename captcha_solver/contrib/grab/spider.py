import logging

from grab.spider.task import Task
from captcha_solver.error import SolutionNotReady, CaptchaServiceError

logger = logging.getLogger('grab.spider.captcha')


class CaptchaSolverInterface(object):
    def task_download_captcha(self, grab, task):
        logger.debug('Got captcha image')
        g_new = self.solver.backend.get_submit_captcha_request(grab.response.body)
        yield Task('submit_captcha', grab=g_new, meta=task.meta)

    def task_submit_captcha(self, grab, task):
        captcha_id = self.solver.backend.parse_submit_captcha_response(grab.response)
        g_new = self.solver.backend.get_check_solution_request(captcha_id)
        yield Task('check_solution', grab=g_new, delay=5, meta=task.meta)

    def task_check_solution(self, grab, task):
        try:
            solution = self.solver.backend.parse_check_solution_response(grab.response)
        except SolutionNotReady:
            logger.debug('Solution is not ready')
            yield task.clone(delay=task.original_delay)
        else:
            logger.debug('Got captcha solution: %s' % solution)
            yield task.meta['handler'](solution, task.meta)


def solve_captcha(solver, grab, url=None, delay=5, recognition_time=120, **kwargs):
    """
    :param solver: CaptchaService object
    :param grab: grab object with captcha image in body
    :return: grab object with captcha solution

    The function is subroutine that must be used in the inline task:

    @inline_task
    def task_foo(self, grab, task):
        url = 'http://example.com/register'
        grab.setup(url=url)
        grab = yield Task(grab=grab)

        captcha_grab = grab.clone()
        url = 'http://example.com/captcha'
        captcha_grab.setup(url=url)
        captcha_grab = yield Task(grab=captcha_grab)
        solution_grab = yield solve_captcha(solver, captcha_grab)
        solution = solver.backend.parse_check_solution_response(solution_grab.response)

    """
    if url:
        grab = grab.clone()
        grab.setup(url=url)
        grab = yield Task(grab=grab)

    antigate_grab = solver.backend.get_submit_captcha_request(grab.response.body, **kwargs)
    antigate_grab = yield Task(grab=antigate_grab)

    captcha_id = solver.backend.parse_submit_captcha_response(antigate_grab.response)
    antigate_grab = solver.backend.get_check_solution_request(captcha_id)

    for _ in xrange(0, recognition_time/delay, delay):
        antigate_grab = yield Task(grab=antigate_grab, delay=delay)
        try:
            solver.backend.parse_check_solution_response(antigate_grab.response)
        except SolutionNotReady:
            pass
        else:
            return