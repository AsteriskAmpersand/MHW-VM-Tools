# -*- coding: utf-8 -*-
"""
Created on Wed Jun 17 06:03:23 2020

@author: AsteriskAmpersand
"""

from mathutils import Vector
import array

def denormalize(vector):
    x,y,z = vector.x, vector.y, vector.z
    maxima = max(abs(x),abs(y),abs(z))
    if maxima == 0: maxima = 1
    x,y,z = round(127*x/maxima), round(127*y/maxima), round(127*z/maxima)
    return [x,y,z,0]

def rescale(vector):
    return list(map(round,(vector.normalized()*127)))

def normalize(vecstruct):
    vector = Vector([vecstruct.x,vecstruct.y,vecstruct.z])
    vector.normalize()
    return vector

def setNormals(mesh,normals):
    space_transform = mesh.rotation_euler
    for v in normals:
        v.rotate(space_transform) 
    meshpart = mesh.data
    meshpart.use_auto_smooth = True
    
    #for l in meshpart.loops:
    #    l.normal[:] = normals[l.vertex_index]
    #meshpart.normals_split_custom_set_from_vertices(normals)

    meshpart.calc_normals_split()
    cl_nors = array.array('f', [0.0] * (len(meshpart.loops) * 3))
    meshpart.loops.foreach_get('normal', cl_nors)
    meshpart.polygons.foreach_set('use_smooth', [False] * len(meshpart.polygons))
    nors_split_set = tuple(zip(*(iter(cl_nors),) * 3))
    meshpart.normals_split_custom_set(nors_split_set)
    meshpart.normals_split_custom_set_from_vertices(normals)
    # Enable the use custom split normals data
    mesh.data.calc_normals_split()
    meshpart.update(calc_edges = True, calc_tessface=True)

def extendBasis(vec):
    if vec[0] != 0:
        return Vector([0,0,1])
    else:
        return Vector([1,0,0])

def getBNormals(mesh):
    normals = {}
    tangents = {}
    mesh.data.calc_normals_split()
    mesh.data.update(calc_edges=True, calc_tessface=True)
    for loop in mesh.data.loops:
        vNormal = rescale(loop.normal)
        vTangent = rescale(loop.tangent)
        if loop.vertex_index in normals and \
            any([not (-1<=(c0-c1)<=1) for c0,c1 in zip(normals[loop.vertex_index],vNormal) ]):
                pass #Mismatch on clnors
            #bpy.context.scene.cursor_location = mesh.vertices[loop.vertex_index].co
            #errorHandler.duplicateNormal(loop.vertex_index, vNormal, vTangent, normals)
        else:
            normals[loop.vertex_index] = vNormal
            tangents[loop.vertex_index] = vTangent
    nor = []
    tan = []
    for i,v in enumerate(mesh.data.vertices):
        if i not in normals: nor.append(v.normal)
        else: nor.append(normals[i])
        if i not in tangents: nor[i].cross(extendBasis(nor[i]))
        else: tan.append(tangents[i])
    return nor, tan

def vertOrderingToNormalList(vertOrdering,normals):    
    clnor = [None]*(max(map(max,vertOrdering))+1)
    for g,n in zip(vertOrdering,normals):
        for vix in g:
            clnor[vix] = normalize(n)
    return clnor