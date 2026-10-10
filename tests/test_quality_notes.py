import unittest
from core.quality_notes import quality_notes


class QualityNotesTests(unittest.TestCase):
    def test_png_original_receives_credit_without_promising_game_quality(self):
        notes = quality_notes({
            'albedo_method':'png_original', 'uv_mode':'original',
            'triangle_retention_percent':97,'texture_bake_size':2048})
        self.assertIn('PNG preservadas',notes[0])
        self.assertFalse(any('perda de nitidez' in n for n in notes))
        self.assertIn('Valide no TaleSpire',notes[-1])

    def test_multi_atlas_and_decimation_are_explained(self):
        notes=quality_notes({
            'albedo_method':'cycles_baked','uv_mode':'repacked',
            'triangle_retention_percent':55,'texture_bake_size':4096})
        text=' '.join(notes)
        for part in ('cabelo','55.0%','2048 px','perda de nitidez'):
            self.assertIn(part,text)

    def test_missing_or_invalid_statistics_are_safe(self):
        self.assertTrue(quality_notes({}))
        self.assertTrue(quality_notes({'triangle_retention_percent':'invalid'}))


if __name__ == '__main__':
    unittest.main()
