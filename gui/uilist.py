# -*- coding: utf-8 -*-
"""
Created on Tue Jun 16 23:20:11 2020

@author: AsteriskAmpersand
"""


import bpy

from bpy.props import (IntProperty,
                       BoolProperty,
                       StringProperty,
                       CollectionProperty,
                       PointerProperty)

from bpy.types import (Operator,
                       Panel,
                       PropertyGroup,
                       UIList)

from bpy_extras.io_utils import ImportHelper

debug = False

# -------------------------------------------------------------------
#   Operators
# -------------------------------------------------------------------

def addMeshAsSilvKey(scn,mesh):
    if len(scn.mhw_silv_keys):
        markKey(mesh)
    else:
        markKey(mesh,False)
    item = scn.mhw_silv_keys.add()
    item.mesh = mesh
    item.obj_type = mesh.type
    item.obj_id = len(scn.mhw_silv_keys)
    scn.mhw_silv_key_index = len(scn.mhw_silv_keys)-1
    return item

class SilvKeys_actions(Operator):
    """Move items up and down, add and remove"""
    bl_idname = "scene.silv_keys_actions"
    bl_label = "SilvKey Actions"
    bl_description = "Move items up and down, add and remove"
    bl_options = {'REGISTER','UNDO'}

    action = bpy.props.EnumProperty(
        items=(
            ('UP', "Up", ""),
            ('DOWN', "Down", ""),
            ('REMOVE', "Remove", ""),
            ('ADD', "Add", ""),
            ))

    def invoke(self, context, event):
        scn = context.scene
        idx = scn.mhw_silv_key_index
        
        if self.action == 'ADD':
            if all((obj and obj.type == "MESH" for obj in bpy.selection)):
                for mesh in bpy.selection:
                    item = addMeshAsSilvKey(context.scene,mesh)
                    info = '"%s" added to list' % (item.mesh.name)
                    self.report({'INFO'}, info)
            else:
                self.report({'INFO'}, "Invalid Selection in the Viewport")
            return {"FINISHED"}
        try:
            item = scn.mhw_silv_keys[idx]
        except IndexError:
            pass
        else:
            if self.action == 'DOWN' and idx < len(scn.mhw_silv_keys) - 1:
                scn.mhw_silv_keys.move(idx, idx+1)
                scn.mhw_silv_key_index += 1
                info = 'Item "%s" moved to position %d' % (item.mesh.name, scn.mhw_silv_key_index + 1)
            elif self.action == 'UP' and idx >= 1:
                scn.mhw_silv_keys.move(idx, idx-1)
                scn.mhw_silv_key_index -= 1
                info = 'Item "%s" moved to position %d' % (item.mesh.name, scn.mhw_silv_key_index + 1)
            elif self.action == 'REMOVE':
                info = 'Item "%s" removed from list' % (scn.mhw_silv_keys[idx].name)
                scn.mhw_silv_key_index -= 1
                scn.mhw_silv_keys.remove(idx)
            self.report({'INFO'}, info)
        return {"FINISHED"}


class SilvKeys_clearList(Operator):
    """Clear all items of the list"""
    bl_idname = "scene.silv_keys_clear_list"
    bl_label = "Clear List"
    bl_description = "Clear all items of the list"
    bl_options = {'REGISTER','UNDO'}

    @classmethod
    def poll(cls, context):
        return bool(context.scene.mhw_silv_keys)

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        if bool(context.scene.mhw_silv_keys):
            context.scene.mhw_silv_keys.clear()
            self.report({'INFO'}, "All items removed")
        else:
            self.report({'INFO'}, "Nothing to remove")
        return{'FINISHED'}

class SilvKeys_clearInvalid(Operator):
    """Clear all items of the list"""
    bl_idname = "scene.silv_keys_clear_invalid"
    bl_label = "Clear Invalid"
    bl_description = "Clear invalid meshes from the list"
    bl_options = {'REGISTER','UNDO'}

    @classmethod
    def poll(cls, context):
        return bool(context.scene.mhw_silv_keys)

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        if bool(context.scene.mhw_silv_keys):
            for ix,v in reversed(list(enumerate(context.scene.mhw_silv_keys))):
                if v is None or v.mesh is None or context.scene.objects.get(v.mesh.name) is None:
                    context.scene.mhw_silv_keys.remove(ix)
            self.report({'INFO'}, "All invalid items removed")
        else:
            self.report({'INFO'}, "Nothing to remove")
        return{'FINISHED'}

class SilvKeys_selectItems(Operator):
    """Select Items in the Viewport"""
    bl_idname = "scene.silv_keys_select_items"
    bl_label = "Select Item(s) in Viewport"
    bl_description = "Select Items in the Viewport"
    bl_options = {'REGISTER', 'UNDO'}

    select_all = BoolProperty(
        default=False,
        name="Select all Items of List",
        options={'SKIP_SAVE'})

    @classmethod
    def poll(cls, context):
        return bool(context.scene.mhw_silv_keys)

    def execute(self, context):
        scn = context.scene
        idx = scn.mhw_silv_key_index

        try:
            scn.mhw_silv_keys[idx]
        except IndexError:
            self.report({'INFO'}, "Nothing selected in the list")
            return{'CANCELLED'}

        obj_error = False
        bpy.ops.object.select_all(action='DESELECT')
        if not self.select_all:
            obj = scn.objects.get(scn.mhw_silv_keys[idx].mesh.name, None)
            if not obj: 
                obj_error = True
            else:
                obj.select = True
                info = '"%s" selected in Viewport' % (obj.name)
        else:
            selected_items = []
            unique_objs = set([i.mesh.name for i in scn.mhw_silv_keys])
            for i in unique_objs:
                obj = scn.objects.get(i, None)
                if obj:
                    obj.select = True
                    selected_items.append(obj.name)

            if not selected_items: 
                obj_error = True
            else:
                missing_items = unique_objs.difference(selected_items)
                if not missing_items:
                    info = '"%s" selected in Viewport' \
                        % (', '.join(map(str, selected_items)))
                else:
                    info = 'Missing items: "%s"' \
                        % (', '.join(map(str, missing_items)))
        if obj_error: 
            info = "Nothing to select, object removed from scene"
        self.report({'INFO'}, info)    
        return{'FINISHED'}

def markKey(item,mark = True):
    if mark:
        item.data["Type"] = "MOD3_VM_Mesh"
    else:
        if "Type" in item.data:
                del item.data["Type"]
        
class SilvKeys_mark(Operator):
    """Mark Meshes as SilvKeys"""
    bl_idname = "scene.silv_keys_mark"
    bl_label = "Mark Meshes as SilvKeys"
    bl_description = "Mark Meshes as SilvKeys"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return len(context.scene.mhw_silv_keys)>1

    def execute(self, context):
        scn = context.scene
        for item in scn.mhw_silv_keys[1:]:
            markKey(item.mesh,True)
        info = 'Marked %d meshes as SilvKeys' % (len(scn.mhw_silv_keys)-1) 
        self.report({'INFO'}, info)
        return {"FINISHED"} 
           
class SilvKeys_unmark(Operator):
    """Unmark Meshes as SilvKeys"""
    bl_idname = "scene.silv_keys_unmark"
    bl_label = "Unmark Meshes as SilvKeys"
    bl_description = "Unmark Meshes as SilvKeys"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return len(context.scene.mhw_silv_keys)>0

    def execute(self, context):
        scn = context.scene
        for item in scn.mhw_silv_keys:
            markKey(item,False)            
        info = 'Unmarked %d meshes as SilvKeys' % (len(scn.mhw_silv_keys)-1)   
        self.report({'INFO'}, info)
        return {"FINISHED"} 

def resolveNorTanPath(filepath,nortan):
    keys = [["no_VM","nor_VM","Normal_VM"],["ta_VM","tan_VM","Tangents_VM"]][nortan]
    if "po_VM" in filepath:
        return filepath.replace("po_VM",keys[0])
    if "pos_VM" in filepath:
        return filepath.replace("pos_VM",keys[1])
    if "Position_VM" in filepath:
        return filepath.replace("Position_VM",keys[2])
    return ""

class SilvKeys_browse(Operator,ImportHelper):
    """File Browser"""
    bl_idname = "scene.silv_keys_browse"
    bl_label = "SilvKey Browse"
    bl_description = "Browse for files"
    bl_options = {'REGISTER'}
    
    filter_glob = StringProperty(default='*.tex', options={'HIDDEN'} )
    
    target = bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        scn = context.scene
        if self.target:
            if self.target == "mhw_silv_key_pos" and scn.mhw_silv_key_nor == "":
                nor = resolveNorTanPath(self.filepath,0)
                if nor: scn.mhw_silv_key_nor = nor
            if self.target == "mhw_silv_key_pos" and scn.mhw_silv_key_tan == "":
                tan = resolveNorTanPath(self.filepath,1)
                if tan: scn.mhw_silv_key_tan = tan
            setattr(scn,self.target,self.filepath)
        return {"FINISHED"} 
    
class SilvKeys_clearPath(Operator):
    """Clear Path"""
    bl_idname = "scene.silv_keys_clear_path"
    bl_label = "SilvKey Clear Paths"
    bl_description = "Clear File Paths"
    bl_options = {'REGISTER','UNDO'}
    
    target = bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        scn = context.scene
        if self.target:
            setattr(scn,self.target,"")
        return {"FINISHED"} 
            
# =============================================================================
#  Debug
# =============================================================================
from ..blender.core import getVertexOrderingList
from mathutils import Vector

def writeDebugNormals(outf,normalPacks):
    for pack in normalPacks:
        outf.write("\n")
        for normal in pack:
            outf.write("%d %d %d\n"%tuple( (normal+Vector((1,1,1)))*127 ) )

class DumpNormals(Operator):
    bl_idname = "debug.dump_normal"
    bl_label = "VM Dump"
    bl_description = "Dump Autonormals"
    bl_options = {'REGISTER'}
    def execute(self,context):
        outf = context.scene.debug_normals_file
        normals = []
        with open(outf,"w") as outf:
            vo = getVertexOrderingList(context.scene.mhw_silv_keys[0].mesh)
            for km in context.scene.mhw_silv_keys[1:]:
                mesh = km.mesh
                n = [mesh.data.vertices[next(iter(g))].normal if g else Vector(0,0,0) for g in vo]
                normals.append(n)
            writeDebugNormals(outf,normals)
        return {"FINISHED"}
            
# -------------------------------------------------------------------
#   Drawing
# -------------------------------------------------------------------

class SilvKeys_items(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        mesh = item.mesh
        if mesh is None or context.scene.objects.get(mesh.name) is None:
            row = layout.row()
            row.label("Mesh No Longer Present")
            #remove from list
            #scn = context.scene
            #scn.mhw_silv_key_index -= 1
            return
        split = layout.split(0.2)
        split.label("Key: %d" % (index-1) if index else "Basis")
        custom_icon = "OUTLINER_OB_%s" % item.obj_type
        #split.prop(item, "name", text="", emboss=False, translate=False, icon=custom_icon)
        split.label(mesh.name, icon=custom_icon) # avoids renaming the item by accident

    def invoke(self, context, event):
        pass   

class SilvKeys_objectList(Panel):
    """Creates a Panel in the Tool Shelf"""
    bl_label = "VM SilvKeys Tools"
    bl_idname = "VM SilvKeys Tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = "MHW Tools"

    def draw(self, context):
        layout = self.layout
        scn = bpy.context.scene

        rows = 4
        row = layout.row()
        row.template_list("SilvKeys_items", "", scn, "mhw_silv_keys", scn, "mhw_silv_key_index", rows=rows)

        col = row.column(align=True)
        col.operator("scene.silv_keys_actions", icon='ZOOMIN', text="").action = 'ADD'
        col.operator("scene.silv_keys_actions", icon='ZOOMOUT', text="").action = 'REMOVE'
        col.separator()
        col.operator("scene.silv_keys_actions", icon='TRIA_UP', text="").action = 'UP'
        col.operator("scene.silv_keys_actions", icon='TRIA_DOWN', text="").action = 'DOWN'

        row = layout.row()
        col = row.column(align=True)
        row = col.row(align=True)
        row.operator("scene.silv_keys_select_items", icon="VIEW3D", text="Select Item")
        row.operator("scene.silv_keys_select_items", icon="GROUP", text="Select all Items").select_all = True
        
        row = col.row(align=True)
        row.operator("scene.silv_keys_mark", icon="RESTRICT_VIEW_OFF", text="Mark SilvKeys")
        row.operator("scene.silv_keys_unmark", icon="RESTRICT_VIEW_ON", text="Unmark SilvKeys")
        
        row = col.row(align=True)
        row.operator("scene.silv_keys_clear_list", icon="X")
        row.operator("scene.silv_keys_clear_invalid", icon="X")
        col.separator()
        
        row = col.row(align=True)
        row.prop(scn, "mhw_silv_key_pos", text = 'Pos')
        row.operator("scene.silv_keys_clear_path",icon="X",text = "").target = "mhw_silv_key_pos"
        row.operator("scene.silv_keys_browse",icon="FILESEL",text = "").target = "mhw_silv_key_pos"
        row = col.row(align=True)
        row.prop(scn, "mhw_silv_key_nor", text = 'Nor')        
        row.operator("scene.silv_keys_clear_path",icon="X",text = "").target = "mhw_silv_key_nor"
        row.operator("scene.silv_keys_browse",icon="FILESEL",text = "").target = "mhw_silv_key_nor"
        row = col.row(align=True)
        row.prop(scn, "mhw_silv_key_tan", text = 'Tan')
        row.operator("scene.silv_keys_clear_path",icon="X",text = "").target = "mhw_silv_key_tan"
        row.operator("scene.silv_keys_browse",icon="FILESEL",text = "").target = "mhw_silv_key_tan"
        
        col.separator()
        row = col.row(align=True)
        row.operator("scene.silv_keys_import",text = "Import")
        row.operator("scene.silv_keys_import",text = "Import All").import_all = True        
        row = col.row(align=True)
        row.operator("scene.silv_keys_export",text = "Export")
        row.operator("scene.silv_keys_export",text = "Export All").export_all = True

        col.separator()
        row = col.row(align=True)
        row.operator("scene.silv_keys_decompile",text = "Decompile To Shapekey")
        row.operator("scene.silv_keys_compile",text = "Compile From Shapekey")
        row = col.row(align=True)
        row.operator("scene.silv_keys_decompile",text = "Decompile & Keyframe").add_keyframes = True
        row.operator("scene.silv_keys_compile_keyframe",text = "Compile From Keyframes")
        row = col.row(align=True)
        row.prop(scn, "mhw_silv_key_freq", text = 'Frame Frequency')
        
        if debug:            
            col.separator()
            row = col.row(align=True)
            row.prop(scn, "debug_normals_file", text = 'Nor')
            row.operator("scene.silv_keys_clear_path",icon="X",text = "").target = "debug_normals_file"
            row.operator("scene.silv_keys_browse",icon="FILESEL",text = "").target = "debug_normals_file"
            row = col.row(align=True)
            row.operator("debug.dump_normal",text = "Dump Normals Raw")

# -------------------------------------------------------------------
#   Collection
# -------------------------------------------------------------------

class SilvKeys_objectCollection(PropertyGroup):
    #name = StringProperty() -> Instantiated by default
    mesh = PointerProperty(
        name="SilvKey Mesh",
        type=bpy.types.Object)
    obj_id = IntProperty()
    obj_type = StringProperty()
    
    @property
    def name(self):
        return self.mesh.name
