# Copyright 2020 Google LLC, Derek Liu
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Implementation of blender backend."""

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------

import bpy
from tensorflow_graphics.viewer import interface

class Object3D(interface.Object3D):
  def __init__(self, blender_object): #, name=None):
    super().__init__(self)
    self._blender_object = blender_object
    # if self.name: self._blender_object.name = self.name

  @property
  def position(self):
    return super().position
  @position.setter
  def position(self, value):
    interface.Object3D.position.__set__(self, value)
    # (UI: click mesh > Transform > Location)
    self._blender_object.location = self.position 

  @property
  def scale(self):
    return super().scale
  @scale.setter
  def scale(self, value):
    interface.Object3D.scale.__set__(self, value)
    # (UI: click mesh > Transform > Scale)
    self._blender_object.scale = self.scale

  @property
  def quaternion(self):
    return super().quaternion
  @quaternion.setter
  def quaternion(self, value):
    interface.Object3D.quaternion.__set__(self, value)
    # (UI: click mesh > Transform > Rotation)
    self._blender_object.rotation_euler = self.quaternion.to_euler()

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------

from tensorflow_graphics.viewer import interface

class Scene(interface.Scene):
  pass

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------

import bpy
from tensorflow_graphics.viewer import interface
from tensorflow_graphics.viewer import blender

class Camera(interface.Camera, blender.Object3D):
  def __init__(self, name=None):
    bpy.ops.object.camera_add() # Created camera with name 'Camera'
    blender.Object3D.__init__(self, bpy.context.object)

class OrthographicCamera(interface.OrthographicCamera, blender.Camera):
  def __init__(self, left=-1, right=+1, top=+1, bottom=-1, near=.1, far=2000):
    interface.OrthographicCamera.__init__(self, left, right, top, bottom, near, far)
    blender.Camera.__init__(self)
    # --- extra things to set
    self._blender_object.data.type = 'ORTHO'
    self._blender_object.data.ortho_scale = 1.0 / self.zoom
    # TODO: integrate the changes from Derek

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------

import bpy
from tensorflow_graphics.viewer import interface

class Renderer(interface.Renderer):

  def __init__(self, numSamples = 128, exposure = 1.5, useBothCPUGPU = False):
    super().__init__()
    # because blender has a default scene on load...
    self.clear_scene()
    # use cycle
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.render.resolution_x = self.width
    bpy.context.scene.render.resolution_y = self.height
    bpy.context.scene.render.film_transparent = True
    # bpy.context.scene.cycles.film_transparent = True # TODO(derek) why is this necessary?
    bpy.context.scene.cycles.samples = numSamples
    bpy.context.scene.cycles.max_bounces = 6
    bpy.context.scene.cycles.film_exposure = exposure
    bpy.data.scenes[0].view_layers['View Layer']['cycles']['use_denoising'] = 1

    # set devices # TODO derek?
    cyclePref  = bpy.context.preferences.addons['cycles'].preferences
    cyclePref.compute_device_type = 'CUDA'
    for dev in cyclePref.devices:
      if dev.type == "CPU" and useBothCPUGPU is False:
        dev.use = False
      else:
        dev.use = True
    bpy.context.scene.cycles.device = 'GPU'

    # TODO derek?
    for dev in cyclePref.devices:
      print (dev)
      print (dev.use)

  def clear_scene(self):
    bpy.ops.wm.read_homefile()
    bpy.ops.object.select_all(action = 'SELECT')
    bpy.ops.object.delete()

  def default_camera_view(self):
    """Changes the UI so that the default view is from the camera POW."""
    view3d = next(area for area in bpy.context.screen.areas if area.type == 'VIEW_3D')
    view3d.spaces[0].region_3d.view_perspective = 'CAMERA'

  def render(self, scene=None, camera=None, path=None):
    assert path.endswith(".blend") or path.endswith(".png")

    # creates blender file
    if path.endswith(".blend"):
      self.default_camera_view()  
      bpy.ops.wm.save_mainfile(filepath=path)
    
    # renders scene directly to file
    if path.endswith(".png"):
      bpy.data.scenes['Scene'].render.filepath = path
      bpy.data.scenes['Scene'].camera = camera._blender_object
      bpy.ops.render.render(write_still = True)

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------

import bpy
from tensorflow_graphics.viewer import interface
from tensorflow_graphics.viewer import blender

class AmbientLight(interface.AmbientLight):
  def __init__(self, color=0x030303, intensity=1):
    bpy.data.scenes[0].world.use_nodes = True #< TODO: shouldn't use_nodes be moved to scene?
    interface.AmbientLight.__init__(self, color=color, intensity=intensity)

  @property
  def color(self):
    return super().color
  @color.setter
  def color(self, value):
    interface.AmbientLight.color.__set__(self, value)
    bpy.data.scenes[0].world.node_tree.nodes["Background"].inputs['Color'].default_value = self.color

  @property
  def intensity(self):
    return super().intensity
  @intensity.setter
  def intensity(self, value):
    interface.AmbientLight.intensity.__set__(self, value)
    bpy.data.scenes[0].world.node_tree.nodes["Background"].inputs['Strength'].default_value = self.intensity   

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------

import bpy
from tensorflow_graphics.viewer import interface
from tensorflow_graphics.viewer import blender

class DirectionalLight(interface.DirectionalLight, blender.Object3D):
  def __init__(self, color=0xffffff, intensity=1, shadow_softness=.1):
    bpy.ops.object.light_add(type='SUN') # Creates light with name 'Sun'
    blender.Object3D.__init__(self, bpy.context.object)
    self._blender_object.data.use_nodes = True
    interface.DirectionalLight.__init__(self, color=color, intensity=intensity, shadow_softness=shadow_softness)
  
  @property
  def color(self):
    return super().color
  @color.setter
  def color(self, value):
    interface.DirectionalLight.color.__set__(self, value)
    self._blender_object.data.node_tree.nodes["Emission"].inputs['Color'].default_value = self.color

  @property
  def intensity(self):
    return super().intensity
  @intensity.setter
  def intensity(self, value):
    self._intensity = value
    self._blender_object.data.node_tree.nodes["Emission"].inputs['Strength'].default_value = self.intensity

  @property
  def shadow_softness(self):
    return super().shadow_softness
  @shadow_softness.setter
  def shadow_softness(self, value):
    interface.DirectionalLight.shadow_softness.__set__(self, value)
    self._blender_object.data.angle = self.shadow_softness

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------

class BufferAttribute(interface.BufferAttribute):
  pass

class Float32BufferAttribute(interface.Float32BufferAttribute):
  def __init__(self, array, itemSize, normalized=None):
    self.array = array  # TODO: @property

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------

import bpy
from tensorflow_graphics.viewer import interface
from tensorflow_graphics.viewer import blender

class Geometry():
  # TODO: should this inherit Object3D or not?  
  pass

class BoxGeometry(interface.BoxGeometry, blender.Object3D):
  def __init__(self, width=1.0, height=1.0, depth=1.0):
    assert width==height and  width==depth, "blender only creates unit cubes"
    bpy.ops.mesh.primitive_cube_add(size=width)
    blender.Object3D.__init__(self, bpy.context.object)
    interface.BoxGeometry.__init__(self, width=width, height=height, depth=depth)

class PlaneGeometry(interface.Geometry, blender.Object3D):
  def __init__(self, width: float=1, height: float=1, widthSegments: int=1, heightSegments: int=1):
    assert widthSegments==1 and  heightSegments==1, "not implemented"
    bpy.ops.mesh.primitive_plane_add()
    blender.Object3D.__init__(self, bpy.context.object)
    
class BufferGeometry(interface.BufferGeometry):
  def __init__(self):
    interface.BufferGeometry.__init__(self)

  def set_index(self, nparray):
    interface.BufferGeometry.set_index(self, nparray)

  def set_attribute(self, name, attribute: interface.BufferAttribute):
    interface.BufferGeometry.set_attribute(self, name, attribute)

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------

#   # TODO: configure shading
#   bpy.ops.object.shade_smooth() # Option1: Gouraud shading
#   # bpy.ops.object.shade_flat() # Option2: Flat shading
#   # edgeNormals(mesh, angle = 10) # Option3: Edge normal shading)

class Material(interface.Material):
  def __init__(self, specs={}):
    # TODO: is this the same as object3D? guess not?
    self._blender_material = bpy.data.materials.new('Material')

  def blender_apply(self, blender_object):
    """Used by materials that need to access the blender object."""
    pass

class MeshBasicMaterial(interface.MeshBasicMaterial, blender.Material):
  def __init__(self, specs={}):
    blender.Material.__init__(self, specs)
    interface.MeshBasicMaterial.__init__(self, specs)

class MeshPhongMaterial(interface.MeshPhongMaterial, blender.Material):
  def __init__(self, specs={}):
    blender.Material.__init__(self, specs)
    interface.Material.__init__(self, specs=specs)
    # TODO: apply specs

  def blender_apply(self, blender_object):
    bpy.context.view_layer.objects.active = blender_object
    bpy.ops.object.shade_smooth()

class MeshFlatMaterial(interface.MeshFlatMaterial, blender.Material):
  def __init__(self, specs={}):
    blender.Material.__init__(self, specs)
    interface.Material.__init__(self, specs=specs)
  
  def blender_apply(self, blender_object):
    bpy.context.view_layer.objects.active = blender_object
    bpy.ops.object.shade_flat()

class ShadowMaterial(interface.ShadowMaterial, blender.Material):
  def __init__(self, specs={}):
    blender.Material.__init__(self, specs=specs)
    interface.ShadowMaterial.__init__(self, specs=specs)

  def blender_apply(self, blender_object):
    if self.receive_shadow:
      blender_object.cycles.is_shadow_catcher = True

# ------------------------------------------------------------------------------
# ----------------------------  mesh.py submodule  -----------------------------
# ------------------------------------------------------------------------------

import bpy
from tensorflow_graphics.viewer import interface
from tensorflow_graphics.viewer import blender

class Mesh(interface.Mesh, blender.Object3D):
  def __init__(self, geometry: blender.Geometry, material: blender.Material):
    interface.Mesh.__init__(self, geometry, material)

    # WARNING: differently from threejs, blender creates an object when
    # primivitives are created, so we need to make sure we do not duplicate it
    if isinstance(geometry, blender.Object3D):
      blender.Object3D.__init__(self, geometry._blender_object)
    else:
      bpy.ops.object.add(type="MESH")
      blender.Object3D.__init__(self, bpy.context.object)
    
    # TODO: is there a better way to achieve this?
    if isinstance(self.geometry, blender.BufferGeometry):
      vertices = self.geometry.attributes["position"].array.tolist()
      faces = self.geometry.index.tolist()
      self._blender_object.data.from_pydata(vertices, [], faces)

    # Adds the material to the object
    self._blender_object.data.materials.append(material._blender_material)
    self.material.blender_apply(self._blender_object)