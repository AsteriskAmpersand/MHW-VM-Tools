# -*- coding: utf-8 -*-
"""
Created on Wed Jun 17 07:32:22 2020

@author: AsteriskAmpersand
"""
from bpy.props import (IntProperty,
                       BoolProperty,
                       StringProperty,
                       CollectionProperty,
                       PointerProperty)

from bpy.types import (Operator,
                       Panel,
                       PropertyGroup,
                       UIList)
import bpy
import bmesh
from ..gui.uilist import addMeshAsSilvKey, markKey

def addKeyframes(context,basis):
    freq = max(1,context.scene.mhw_silv_key_freq)
    for i, keyblock in enumerate(basis.data.shape_keys.key_blocks):
       #context.scene.frame_current = i*10
       basis.data.shape_keys.eval_time = i*freq
       basis.data.shape_keys.keyframe_insert("eval_time", frame=i*freq)
    context.scene.frame_start = 0
    context.scene.frame_end = i*freq
        
class SilvKeys_decompile(Operator):
    """File Browser"""
    bl_idname = "scene.silv_keys_decompile"
    bl_label = "SilvKey Decompile"
    bl_description = "Destructive Conversion of SilvKeys to Shapekeys"
    bl_options = {'REGISTER','UNDO'}
    
    add_keyframes = BoolProperty(
            name = "Add keyframes to the shapekeys",
            description = "Keyframe the shapekey.",
            default = False,
            )
    
    def execute(self, context):
        scn = context.scene
        
        basis = scn.mhw_silv_keys[0].mesh
        objs = bpy.data.objects
        skB = basis.shape_key_add("Basis")
        skB.interpolation = 'KEY_LINEAR'
        
        
        for i,key in enumerate(scn.mhw_silv_keys[1:]):
            k = key.mesh
            sk = basis.shape_key_add(k.name)
            sk.interpolation = 'KEY_LINEAR'
        
            # position each vert
            for i in range(len(basis.data.vertices)):
                sk.data[i].co = k.data.vertices[i].co
            #sk.keyframe_insert("value", frame=i*10)
            objs.remove(k,do_unlink=True)
        basis.data.shape_keys.use_relative = False
        bpy.ops.scene.silv_keys_clear_list()
        if self.add_keyframes:
            addKeyframes(context,basis)
        return {"FINISHED"}
    
    @classmethod
    def poll(cls,context):
        return len(context.scene.mhw_silv_keys)>1
    
class SilvKeys_compile(Operator):
    """File Browser"""
    bl_idname = "scene.silv_keys_compile"
    bl_label = "SilvKey Compile"
    bl_description = "Destructive Conversion of Shapekeys to Silvkeys"
    bl_options = {'REGISTER','UNDO'}
    
    def execute(self, context):
        #return {"FINISHED"}
        if bool(context.scene.mhw_silv_keys):
            context.scene.mhw_silv_keys.clear()
        obj = context.object
        
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        for shapekey in bm.verts.layers.shape.keys():
            if shapekey != "Basis":
                key = bm.verts.layers.shape.get(shapekey)
                km = bmesh.new()
                km.from_mesh(context.object.data)
                bm.verts.ensure_lookup_table()
                km.verts.ensure_lookup_table()
                for i in range(len(km.verts)):
                    km.verts[i].co = bm.verts[i][key]
                mesh_data = bpy.data.meshes.new(shapekey)
                km.to_mesh(mesh_data)
                mesh_data.update(calc_edges = True, calc_tessface=True)
                mesh_data.calc_normals_split()
                obj = bpy.data.objects.new(shapekey, mesh_data)
                context.scene.objects.link(obj)
            else:
                obj = context.object
            addMeshAsSilvKey(context.scene,obj)
            markKey(obj)
            
        for key in reversed(context.object.data.shape_keys.key_blocks):
            context.object.shape_key_remove(key)
            
        return {"FINISHED"} 
    
    @classmethod
    def poll(cls,context):
        return context.object and hasattr(context.object,"data") and hasattr(context.object.data,"shape_keys")


#silv_keys_compile_keyframe
class SilvKeys_compile_keyframes(Operator):
    """File Browser"""
    bl_idname = "scene.silv_keys_compile_keyframe"
    bl_label = "SilvKey Compile Keyframes"
    bl_description = "Destructive Conversion of Keyframed Shapekeys to Silvkeys"
    bl_options = {'REGISTER','UNDO'}
    
    def execute(self, context):
        #return {"FINISHED"}
        if bool(context.scene.mhw_silv_keys):
            context.scene.mhw_silv_keys.clear()
        obj = context.object
        scene = bpy.context.scene
        frameRange = scene.frame_start, scene.frame_end+1
        scene.frame_current = frameRange[0]
        freq = max(1,scene.mhw_silv_key_freq)
        basis = None
        for k in range(frameRange[0],frameRange[1],freq):
            scene.frame_set(k)
            mesh = obj.to_mesh(scene,True,'PREVIEW')
            mesh.transform(obj.matrix_world)
            
            mesh_obj = bpy.data.objects.new(obj.name+"_SilvKey",mesh)
            scene.objects.link(mesh_obj)
            
            addMeshAsSilvKey(context.scene,mesh_obj)
            if basis is None: basis = mesh_obj
            
        if basis is not None:
            name = obj.name
            for prop in obj.data.keys():
                basis.data[prop] = obj.data[prop]
            for prop in obj.keys():
                basis[prop] = obj[prop]
            objs = bpy.data.objects
            objs.remove(obj,do_unlink = True)
            basis.name = name
        return {"FINISHED"} 
    
    @classmethod
    def poll(cls,context):
        return context.object and context.object.type == "MESH"