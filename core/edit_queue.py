"""Ordered desktop edits, with a publication barrier on the caller's thread."""
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass


@dataclass
class Edit:
    work: object
    complete: object
    key: object = None
    merge: object = None


class EditQueue:
    """One worker; pending motion can merge across no command/click boundary.

    Workers never call Tk. Poll only while busy. The next operation cannot touch
    the session until the caller has published the previous operation's result.
    """
    def __init__(self):
        self.pending = deque()
        self.active = None
        self.closed = False
        self.closing_errors = []
        self.pool = ThreadPoolExecutor(max_workers=1,thread_name_prefix='AstronyxEdit')

    @property
    def busy(self):
        return self.active is not None or bool(self.pending)

    def submit(self, work, complete, *, key=None, merge=None, payload=None):
        if self.closed:
            return
        if key is not None and self.pending and self.pending[-1].key == key:
            self.pending[-1].merge(payload)
            return
        self.pending.append(Edit(work,complete,key,merge))
        self._start()

    def _start(self):
        if not self.closed and self.active is None and self.pending:
            edit = self.pending.popleft()
            self.active = edit,self.pool.submit(edit.work)

    def poll(self):
        if self.closed or self.active is None:
            return
        edit,future = self.active
        if not future.done():
            return
        try:
            result,error = future.result(),None
        except Exception as exc:
            result,error = None,exc
        try:
            edit.complete(result,error)
        finally:
            self.active = None
            self._start()

    def close(self, *, drain=False):
        if self.closed:
            return None
        self.closed = True
        pending = list(self.pending) if drain else []
        self.pending.clear()
        def finish():
            # Requested saves must follow all preceding edits even if the
            # window closes. No completion callback can access a destroyed Tk.
            for edit in pending:
                try:
                    edit.work()
                except Exception as error:
                    self.closing_errors.append(error)
        future = self.pool.submit(finish) if pending else None
        self.pool.shutdown(wait=False,cancel_futures=not drain)
        return future
