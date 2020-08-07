# -*- coding: utf-8 -*-
"""
Created on Fri Jun 19 19:20:40 2020

@author: AsteriskAmpersand
"""


dimension = {}
bm = bmesh.from_edit_mesh(bpy.context.active_object.data)
uv_layer = bm.loops.layers.uv[1]
for face in bm.faces:
    for loop in face.loops:
        uv = loop[uv_layer]
        if uv.uv[1] not in dimension:
            dimension[uv.uv[1]] = 0
        if uv.uv[0] > dimension[uv.uv[1]]:
            dimension[uv.uv[1]] = uv.uv[0]
            
print(dimension)