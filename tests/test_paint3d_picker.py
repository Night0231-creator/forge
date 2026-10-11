"""Raycast-equivalent CPU projection tests: UV, occlusion, camera and no-hit."""
import unittest
import numpy as np
from ui.paint3d_picker import ProjectedUVPicker
from ui.texture_renderer import draw


class Mesh:
    def __init__(self,points,triangles,uv):
        self.points=np.asarray(points,dtype=np.float32)
        self.triangles=np.asarray(triangles,dtype=np.int32)
        self.texcoords=np.asarray(uv,dtype=np.float32)


class ProjectedPickerTests(unittest.TestCase):
    def model(self):
        return Mesh(
            [(-1,-1,0),(1,-1,0),(0,1,0)],
            [(0,1,2)],
            [[(0,0),(1,0),(.5,1)]],
        )

    def test_center_selects_visible_triangle_and_interpolates_uv(self):
        p=ProjectedUVPicker(self.model(),yaw=0,pitch=0,zoom=1,
                            canvas_width=500,canvas_height=500,
                            show_reference=False)
        # Render center is (250,275) with symmetric centered geometry.
        hit=p.hit(250,275)
        self.assertIsNotNone(hit)
        self.assertEqual(hit.triangle,0)
        self.assertAlmostEqual(hit.u,.5,places=5)
        self.assertAlmostEqual(hit.v,.5,places=5)
        self.assertEqual(hit.pixel(101,101),(50,50))
        self.assertIsNone(p.hit(-500,-200))

    def test_occluded_triangle_will_not_be_painted(self):
        # Both overlap onscreen. Larger transformed depth must win.
        model=Mesh(
            [(-1,-1,-1),(1,-1,-1),(0,1,-1),
             (-1,-1,1),(1,-1,1),(0,1,1)],
            [(0,1,2),(3,4,5)],
            [[(0,0),(.2,0),(.1,.2)],[(.8,.8),(1,.8),(.9,1)]],
        )
        pick=ProjectedUVPicker(model,yaw=0,pitch=0,zoom=1,
                               canvas_width=400,canvas_height=400,
                               show_reference=False)
        selected=pick.hit(200,220)
        self.assertIsNotNone(selected)
        self.assertEqual(selected.triangle,1)
        self.assertGreater(selected.u,.7)

    def test_large_canvas_offset_and_camera_pan(self):
        model=self.model()
        pick=ProjectedUVPicker(model,yaw=0,pitch=0,zoom=1,
                               canvas_width=1000,canvas_height=1000,
                               pan_x=31,pan_y=-19,show_reference=False)
        albedo=np.full((8,8,3),(240,20,10),dtype=np.uint8)
        frame=draw(model,albedo,0,0,1,1000,1000,31,-19)
        # Derive the click from the actual renderer, including its image cap.
        px=(1000-frame.width)*.5+frame.width*.5+31
        py=(1000-frame.height)*.5+frame.height*.55-19
        self.assertGreater(frame.getpixel((round(frame.width*.5+31),
                                          round(frame.height*.55-19)))[0],100)
        hit=pick.hit(px,py)
        self.assertIsNotNone(hit)
        self.assertAlmostEqual(hit.u,.5,places=4)
        self.assertAlmostEqual(hit.v,.5,places=4)

    def test_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            ProjectedUVPicker(self.model(),yaw=0,pitch=0,zoom=0,
                              canvas_width=500,canvas_height=500)
        with self.assertRaises(ValueError):
            ProjectedUVPicker(self.model(),yaw=0,pitch=0,zoom=1,
                              canvas_width=50,canvas_height=50)
        p=ProjectedUVPicker(self.model(),yaw=0,pitch=0,zoom=1,
                            canvas_width=300,canvas_height=300)
        self.assertIsNone(p.hit(float('nan'),0))


if __name__=='__main__':
    unittest.main()
