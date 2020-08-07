# -*- coding: utf-8 -*-
"""
Created on Tue Jun 16 22:55:01 2020

@author: AsteriskAmpersand
"""

content=bytes("","UTF-8")
bl_info = {
    "name": "MHW VM Tools",
    "category": "Import-Export",
    "author": "AsteriskAmpersand (Code and Research) & Silvris (Research)",
    "blender": (2, 79, 0),
    "location": "View3D > MHW Tools > Mod3/MHW",
    "version": (1,0,0)
}
 
import bpy, os,sys
import importlib

from bpy.props import (IntProperty,
                       BoolProperty,
                       StringProperty,
                       CollectionProperty,
                       PointerProperty,
                       FloatProperty)

from bpy.types import (Operator,
                       Panel,
                       PropertyGroup,
                       UIList)


from .gui import uilist
from .blender import core
from .blender import shapekeys
from .common.selection import Selection

# importlib.reload(dpmhw_arrangers)
# importlib.reload(usual_operators)
importlib.reload(uilist)
# -------------------------------------------------------------------
#   Register & Unregister
# -------------------------------------------------------------------

classes = (
    Selection,
    uilist.SilvKeys_actions,
    uilist.SilvKeys_clearList,
    uilist.SilvKeys_clearInvalid,
    uilist.SilvKeys_items,
    uilist.SilvKeys_selectItems,
    uilist.SilvKeys_objectList,
    uilist.SilvKeys_objectCollection,
    uilist.SilvKeys_mark,
    uilist.SilvKeys_unmark,
    uilist.SilvKeys_browse,
    uilist.SilvKeys_clearPath,
    core.SilvKeys_import,
    core.SilvKeys_export,
    shapekeys.SilvKeys_compile,
    shapekeys.SilvKeys_decompile,
    shapekeys.SilvKeys_compile_keyframes,
    core.SilvKeys_import_menu,
    core.SilvKeys_export_menu,
    
    uilist.DumpNormals
)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
        
    # Menus
    bpy.types.INFO_MT_file_import.append(core.menu_func_import)
    bpy.types.INFO_MT_file_export.append(core.menu_func_export)

    # Custom scene properties
    bpy.types.Scene.mhw_silv_keys = CollectionProperty(type=uilist.SilvKeys_objectCollection)
    bpy.types.Scene.mhw_silv_key_index = IntProperty()
    bpy.types.Scene.mhw_silv_key_pos = StringProperty()
    bpy.types.Scene.mhw_silv_key_nor = StringProperty()
    bpy.types.Scene.mhw_silv_key_tan = StringProperty()
    bpy.types.Scene.mhw_silv_key_freq = IntProperty(default = 10)
    
    bpy.types.Scene.debug_normals_file = StringProperty()

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)

    bpy.types.INFO_MT_file_import.remove(core.menu_func_import)
    bpy.types.INFO_MT_file_export.remove(core.menu_func_export)

    del bpy.types.Scene.mhw_silv_keys
    del bpy.types.Scene.mhw_silv_key_index
    del bpy.types.Scene.mhw_silv_key_pos
    del bpy.types.Scene.mhw_silv_key_nor
    del bpy.types.Scene.mhw_silv_key_tan
    del bpy.types.Scene.mhw_silv_key_freq 
    
    del bpy.types.Scene.debug_normals_file

#if __name__ == "__main__":
#    register()