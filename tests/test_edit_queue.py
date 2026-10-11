"""Publication ordering, motion merging, errors and editor shutdown."""
import threading
import time
import unittest
from core.edit_queue import EditQueue
from ui.painting_studio import PaintingStudio


class EditQueueTests(unittest.TestCase):
    def setUp(self):
        self.edits=EditQueue()
        self.addCleanup(self.edits.close)

    def drain(self):
        deadline=time.perf_counter()+5
        while self.edits.busy and time.perf_counter()<deadline:
            self.edits.poll()
            time.sleep(.001)
        self.assertFalse(self.edits.busy)

    def test_work_is_off_thread_and_completion_precedes_next_edit(self):
        main=threading.get_ident();events=[]
        def first():
            self.assertNotEqual(threading.get_ident(),main)
            events.append('paint');return 12
        def publish(value,error):
            self.assertEqual(threading.get_ident(),main)
            self.assertIsNone(error);self.assertEqual(value,12)
            events.append('publish')
            # Submitting from completion must still honor its publication barrier.
            self.edits.submit(lambda:events.append('save'),lambda *_:None)
            time.sleep(.01)
            self.assertEqual(events,['paint','publish'])
        self.edits.submit(first,publish)
        self.drain()
        self.assertEqual(events,['paint','publish','save'])

    def test_merge_keeps_motion_and_cannot_cross_undo_or_click(self):
        gate=threading.Event();self.addCleanup(gate.set)
        events=[];path=[(0,0),(1,0)]
        self.edits.submit(lambda:gate.wait(5),lambda *_:None)
        self.edits.submit(lambda:events.append(tuple(path)),lambda *_:None,
            key=1,merge=lambda points:PaintingStudio._extend_path(path,points),payload=path)
        self.edits.submit(lambda:None,lambda *_:None,key=1,merge=lambda _:None,
                          payload=[(1,0),(2,0),(2,2),(3,2)])
        self.edits.submit(lambda:events.append('undo'),lambda *_:None)
        self.edits.submit(lambda:events.append('next stroke'),lambda *_:None,
                          key=1,merge=lambda _:None,payload=[])
        self.assertEqual(len(self.edits.pending),3)
        gate.set();self.drain()
        self.assertEqual(events,[((0,0),(2,0),(2,2),(3,2)),'undo','next stroke'])

    def test_error_does_not_stop_later_commands(self):
        errors=[];events=[]
        def fail():raise ValueError('bad stamp')
        self.edits.submit(fail,lambda value,error:errors.append(error))
        self.edits.submit(lambda:events.append('undo'),lambda *_:None)
        self.drain()
        self.assertIsInstance(errors[0],ValueError)
        self.assertEqual(events,['undo'])

    def test_close_cancels_pending_without_publishing_to_destroyed_widgets(self):
        gate=threading.Event();self.addCleanup(gate.set)
        published=[];pending=[]
        self.edits.submit(lambda:gate.wait(5),lambda *_:published.append(True))
        self.edits.submit(lambda:pending.append(True),lambda *_:published.append(True))
        future=self.edits.active[1]
        self.edits.close();gate.set();future.result(timeout=5)
        self.edits.poll()
        self.assertEqual(published,[]);self.assertEqual(pending,[])

    def test_requested_save_finishes_after_preceding_edits_on_close(self):
        gate=threading.Event();self.addCleanup(gate.set)
        events=[];published=[]
        self.edits.submit(lambda:gate.wait(5),lambda *_:published.append(True))
        self.edits.submit(lambda:events.append('paint'),lambda *_:published.append(True))
        self.edits.submit(lambda:events.append('save'),lambda *_:published.append(True))
        finishing=self.edits.close(drain=True)
        gate.set();finishing.result(timeout=5)
        self.edits.poll()
        self.assertEqual(events,['paint','save']);self.assertEqual(published,[])


if __name__=='__main__':unittest.main()
