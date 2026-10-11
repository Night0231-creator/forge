"""V2.4 layers/region selection/MAES channel safety regression."""
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from core.layered_materials import (
    LayeredPaintSession, PRESETS, apply_materials_to_export,
)


class MaterialWorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)/'Knight'
        for part in ('TaleWeaverLite','TaleWeaverCmd_Source','Entrada_TaleWeaverCmd'):
            (self.root/part).mkdir(parents=True)
        self.original=self.root/'TaleWeaverLite/Albedo.png'
        albedo=Image.new('RGB',(32,32),'#505050')
        ImageDraw.Draw(albedo).rectangle((0,0,15,31),fill='#DD0000')
        for path in (self.original,
                     self.root/'TaleWeaverCmd_Source/Albedo.png',
                     self.root/'Entrada_TaleWeaverCmd/albedo.png'):
            albedo.save(path)
        maes=Image.new('RGBA',(32,32),(4,210,5,50))
        for path in (self.root/'TaleWeaverLite/MAES.png',
                     self.root/'TaleWeaverCmd_Source/MAES.png',
                     self.root/'Entrada_TaleWeaverCmd/metallic_ao_emis_smoothness.png'):
            maes.save(path)
        self.tsmod=self.root/'Knight.tsMod'
        self.tsmod.write_bytes(b'untouched binary tsMod')

    def tearDown(self):
        self.temp.cleanup()

    def session(self):
        return LayeredPaintSession(self.original,self.root)

    def test_layers_visibility_opacity_order_and_undo(self):
        s=self.session()
        self.assertEqual(len(s.layers),1)
        s.checkpoint()
        s.stroke((6,6),(6,6),'#00FF00',size=5)
        self.assertEqual(s.pick(6,6),'#00FF00')
        s.add_layer('Brasão')
        s.stroke((6,6),(6,6),'#0000FF',size=5)
        self.assertEqual(s.pick(6,6),'#0000FF')
        s.set_visible(False)
        self.assertEqual(s.pick(6,6),'#00FF00')
        self.assertTrue(s.undo())
        self.assertEqual(s.pick(6,6),'#0000FF')
        s.set_opacity(0)
        self.assertEqual(s.pick(6,6),'#00FF00')
        self.assertTrue(s.undo())
        self.assertEqual(s.layers[1].opacity,100)
        self.assertEqual(s.pick(6,6),'#0000FF')
        s.remove_layer()
        self.assertEqual(len(s.layers),1)
        self.assertEqual(s.pick(6,6),'#00FF00')
        with self.assertRaises(ValueError):
            s.remove_layer()

    def test_connected_selection_and_masked_paint(self):
        s=self.session()
        self.assertTrue(s.select_region(5,5,3))
        self.assertEqual(s.selection.getpixel((7,7)),255)
        self.assertEqual(s.selection.getpixel((22,7)),0)
        s.checkpoint()
        s.bucket(5,5,'#0022CC')
        self.assertEqual(s.pick(5,5),'#0022CC')
        self.assertEqual(s.pick(23,5),'#505050')
        s.stroke((15,5),(23,5),'#44EE11',size=7)
        self.assertEqual(s.pick(23,5),'#505050')
        s.clear_region()
        s.checkpoint()
        s.stroke((23,5),(23,5),'#44EE11',size=7)
        self.assertEqual(s.pick(23,5),'#44EE11')

    def test_material_changes_only_selected_maes_channels(self):
        s=self.session()
        with self.assertRaisesRegex(ValueError,'Selecione'):
            s.apply_material('Ouro polido')
        self.assertTrue(s.select_region(4,4,4))
        s.apply_material('Cristal mágico')
        self.assertEqual(s.maes_image.getpixel((5,5)),PRESETS['Cristal mágico'])
        self.assertEqual(s.maes_image.getpixel((20,5)),(4,210,5,50))
        self.assertTrue(s.maes_dirty)
        self.assertTrue(s.undo())
        self.assertEqual(s.maes_image.getpixel((5,5)),(4,210,5,50))
        self.assertFalse(s.maes_dirty)
        self.assertTrue(s.redo())
        self.assertEqual(s.maes_image.getpixel((5,5)),PRESETS['Cristal mágico'])

    def test_saved_layer_project_restores_and_exports_with_backups(self):
        s=self.session()
        s.add_layer('Ouro')
        s.checkpoint()
        s.stroke((4,4),(4,4),'#FFAA00',size=5)
        s.select_region(5,5,7)
        s.apply_material('Ouro polido')
        draft=s.save_draft(self.root)
        self.assertTrue((self.root/'Pintura/camadas/camada_02.png').is_file())
        self.assertTrue(s.material_draft.is_file())
        reopened=self.session()
        self.assertTrue(reopened.restored_layers)
        self.assertEqual(len(reopened.layers),2)
        self.assertEqual(reopened.pick(4,4),'#FFAA00')
        self.assertEqual(reopened.maes_image.getpixel((5,5)),PRESETS['Ouro polido'])
        binary=self.tsmod.read_bytes()
        written=apply_materials_to_export(self.root,draft,s.material_draft)
        self.assertEqual(len(written),6)
        for path in written:
            self.assertEqual(len(list(path.parent.glob(path.name+'.*.bak'))),1)
        with Image.open(self.root/'TaleWeaverCmd_Source/MAES.png') as im:
            self.assertEqual(im.convert('RGBA').getpixel((5,5)),PRESETS['Ouro polido'])
            self.assertEqual(im.convert('RGBA').getpixel((20,5)),(4,210,5,50))
        self.assertEqual(self.tsmod.read_bytes(),binary)
        # Source changed after applying; do not overlay the paint layers twice.
        self.assertFalse(self.session().restored_layers)

    def test_insecure_draft_and_unknown_preset_fail(self):
        s=self.session()
        s.select_region(1,1)
        with self.assertRaises(ValueError):
            s.apply_material('Platina inventada')
        outside=Path(self.temp.name)/'MAES_editado.png'
        Image.new('RGBA',(4,4)).save(outside)
        draft=s.save_draft(self.root)
        with self.assertRaises(ValueError):
            apply_materials_to_export(self.root,draft,outside)
        self.assertFalse(list(self.root.glob('**/*.bak')))


if __name__=='__main__':
    unittest.main()
