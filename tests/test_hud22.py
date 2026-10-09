"""Pure filtering regression tests: no Tk display needed."""
import unittest
from types import SimpleNamespace
from ui.hud22 import filter_miniatures

class Hud22Tests(unittest.TestCase):
    def test_search_case_and_underscore(self):
        items=[SimpleNamespace(name='Eclipse_Warlord',tsmod='ready'),
               SimpleNamespace(name='Ancient_Dragon',tsmod=None)]
        self.assertEqual([x.name for x in filter_miniatures(items,'WAR')],['Eclipse_Warlord'])
        self.assertEqual(len(filter_miniatures(items, '')),2)
    def test_ready_and_pending(self):
        items=[SimpleNamespace(name='Eclipse',tsmod='ready'),SimpleNamespace(name='Dragon',tsmod=None)]
        self.assertEqual(len(filter_miniatures(items,'','Prontos')),1)
        self.assertEqual(filter_miniatures(items,'','Em preparação')[0].name,'Dragon')
        self.assertEqual(len(items),2)
    def test_unknown_term(self):
        self.assertEqual(filter_miniatures([SimpleNamespace(name='Eclipse',tsmod='x')], 'missing'),[])
if __name__ == '__main__':
    unittest.main()
