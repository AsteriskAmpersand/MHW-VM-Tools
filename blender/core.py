# -*- coding: utf-8 -*-
"""
Created on Tue Jun 16 05:59:04 2020

@author: AsteriskAmpersand
"""


import bpy
import bmesh
from bpy.props import (IntProperty,
                       FloatProperty,
                       BoolProperty,
                       StringProperty,
                       CollectionProperty,
                       PointerProperty)

from bpy.types import (Operator,
                       Panel,
                       PropertyGroup,
                       UIList)
from bpy_extras.io_utils import ImportHelper,ExportHelper

from itertools import groupby
from operator import itemgetter
from mathutils import Vector
import math

from .blenderNormals import vertOrderingToNormalList, getBNormals, setNormals
from ..common.Clusters import ClusterSet
from ..gui.uilist import addMeshAsSilvKey,markKey,resolveNorTanPath
from ..struct.Tex import TexFile

class MissingSecondary(Exception):
    pass
class SecondaryAlreadyExists(Exception):
    pass
class UnsplitSeam(Exception):
    pass
class NoShapeKey(Exception):
    pass
class SilvKeysAlreadyPresent(Exception):
    pass
class UVCountMismatch(Exception):
    pass
class VertexCountMismatch(Exception):
    pass

def getVertexOrderingListForceful(mesh):
    """Creates a list of bins for each vertex uv index grouping"""
    if len(mesh.data.uv_layers) < 2:
        raise MissingSecondary()    
    bm = bmesh.new()
    bm.from_mesh(mesh.data)
    bm.verts.ensure_lookup_table()
    bm.verts.index_update() 
    layer = bm.loops.layers.uv[1]
    uvmap = {}
    for face in bm.faces:
        for v in face.loops:
            uv = v[layer].uv
            vindex = v.vert.index
            if vindex in uvmap and uvmap[vindex] != uv[0]:
                raise UnsplitSeam()
            else:
                uvmap[vindex] = uv[0]
    tr = lambda x: tuple(reversed(x))
    return [list(map(itemgetter(0),uv)) for vg,uv in groupby(sorted(uvmap.items(),key = tr),key = itemgetter(1))]

def getVertexOrderingList(mesh):
    """Creates a list of bins for each vertex uv index grouping"""
    if len(mesh.data.uv_layers) < 2:
        raise MissingSecondary()    
    bm = bmesh.new()
    bm.from_mesh(mesh.data)
    bm.verts.ensure_lookup_table()
    bm.verts.index_update() 
    layer = bm.loops.layers.uv[1]
    uvmap = {}
    visited = {}
    M = 0
    for face in bm.faces:
        for v in face.loops:
            uv = v[layer].uv
            vindex = v.vert.index
            uvc = round(uv[0]) + 2048*round(uv[1])
            if uvc not in uvmap:
                uvmap[uvc] = set()
            uvmap[uvc].add(vindex)
            if vindex in visited and visited[vindex] != uvc:
                raise UnsplitSeam()
            else:
                visited[vindex] = uvc
            if uvc > M: M = uvc
    return [uvmap[i] if i in uvmap else [] for i in range(M+1)]

def createVertexOrderingUV(mesh,vertIndex):
    """Creates a UV Layer from the mapping of Vertex Index to VM Position"""
    if len(mesh.data.uv_layers) >= 2:
        raise SecondaryAlreadyExists()
    bm = bmesh.new()
    bm.from_mesh(mesh.data)
    bm.verts.ensure_lookup_table()
    bm.verts.index_update() 
    layer = bm.loops.layers.uv.new()
    for face in bm.faces:
        for v in face.loops:
            v[layer].uv = [vertIndex[v.vert.index]%2048,vertIndex[v.vert.index]//2048]
    bm.to_mesh(mesh.data)
    #mesh.update()
    return

def addShapekey(obj, vertOrd, vmKey = None):
    """Creates a shapekey from a Vertex Ordering family and a VM Key"""
    if vmKey is None:
        kn = "VM Root"
        sk = obj.shape_key_add(kn)
        return
    kn = "VM Key"
    sk = obj.shape_key_add(kn)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    sl = bm.verts.layers.shape.get(kn)
    for ixs,keyV in zip(vertOrd,vmKey):
        for ix in ixs:
            bm.verts[ix][sl]=bm.verts[ix].co+keyV
    bm.to_mesh(obj.data)
    return sk

def applyPosSilvKey(mesh,vertOrdering,posKey):
    bm = bmesh.new()
    bm.from_mesh(mesh.data)
    bm.verts.ensure_lookup_table()
    bm.verts.index_update() 
    for vixs,delta in zip(vertOrdering,posKey):
        for vix in vixs:
            bm.verts[vix].co += Vector([delta.x,delta.y,delta.z])
    bm.to_mesh(mesh.data)

def applyNorSilvKey(keyM,vertOrder,key):
    normals = vertOrderingToNormalList(vertOrder,key)
    setNormals(keyM,normals)
    
def compilePosDelta(meshes):
    key = meshes[0].data
    deltas = []
    for mesh in meshes[1:]:
        delta = []
        for v0,v1 in zip(key.vertices,mesh.data.vertices):
            delta.append(v1.co-v0.co)
        deltas.append(delta)
    return deltas

def compileNorTanDelta(meshes):
    ndelta = []
    tdelta = []
    for mesh in meshes[1:]:
        nor,tan = getBNormals(mesh)
        ndelta.append(nor)
        tdelta.append(tan)
    return ndelta,tdelta

def reorderDelta(vertOrdering,delta):
    return [delta[next(iter(order))] if order else Vector(0,0,0) for order in vertOrdering]
    
# =============================================================================
#  Operators
# =============================================================================

class SilvKeys_import_menu(Operator,ImportHelper):
    bl_idname = "custom_import.silv_keys_import_menu"
    bl_label = "Import VM"
    bl_description = "Imports VMs as SilvKeys"
    bl_options = {'REGISTER', 'PRESET','UNDO'}
    

    filename_ext = ".tex"
    filter_glob = StringProperty(default="*.tex", options={'HIDDEN'}, maxlen=255)
    
    import_all = BoolProperty(name = "Import Normals and Tangents",
                              description = "Imports matching Normal and Tangent VM.",
                              default = True,
                              )
    normal_path = StringProperty(
                                 name = "Normal Map Path",
                                 description = "Path to Normal Input. Set to empty for it to mirror the position path.")
    tangent_path = StringProperty(
                                 name = "Tangent Map Path",
                                 description = "Path to Tangent Input. Set to empty for it to mirror the position path.")
    
    def invoke(self,context,event):
        if context.scene.mhw_silv_key_pos:
            self.filepath = context.scene.mhw_silv_key_pos
        self.normal_path = context.scene.mhw_silv_key_nor
        self.tangent_path = context.scene.mhw_silv_key_tan
        return super().invoke(context,event)
    
    def execute(self,context):
        if context.scene.mhw_silv_keys:
            raise SilvKeysAlreadyPresent("Clear current SilvKeys before importing.")
        baseObj = context.object
        keyMeshes = self.importPosVM(context,baseObj,TexFile(self.filepath))
        if self.import_all:
            if not self.normal_path:
                nor =  resolveNorTanPath(self.filepath,0)
                if nor: self.normal_path = nor
            if not self.tangent_path:
                tan = resolveNorTanPath(self.filepath,1)
                if tan: self.tangent_path = tan  
        if self.import_all and self.normal_path and self.tangent_path:
            self.importNorTanVM(keyMeshes,TexFile(self.normal_path))
        return {'FINISHED'}

    def importPosVM(self,context,baseObj,silvKeysets):
        self.appendKey(context,baseObj)
        keyMeshes = []
        for key in silvKeysets:
            keyM = self.createKeyMesh(context.scene,baseObj)
            vertOrder = getVertexOrderingList(keyM)
            if len(key) > len(vertOrder)+1:
                print("Warning Vector Map has %d UV Entries while Mesh has %d"%(len(key),len(vertOrder)))
            if len(vertOrder) < len(key):
                print("Warning Mesh has %d UV Entries while Mesh has %d"%(len(vertOrder),len(key)))
            applyPosSilvKey(keyM,vertOrder,key)
            self.appendKey(context,keyM)
            keyMeshes.append(keyM)
        return keyMeshes
            
    def importNorTanVM(self,meshes,norKeys):
        for keyM,key in zip(meshes,norKeys):
            vertOrder = getVertexOrderingList(keyM)
            applyNorSilvKey(keyM,vertOrder,key)
    
    def appendKey(self,context,mesh):
        scn = context.scene
        addMeshAsSilvKey(scn,mesh)
        
    def createKeyMesh(self,scn,baseObj):
        me = baseObj.data
        n_me = me.copy()
        ob = bpy.data.objects.new(baseObj.name+"_SilvKey",n_me)
        ob.matrix_world = baseObj.matrix_world
        scn.objects.link(ob)
        scn.update()
        markKey(ob)
        return ob

def vectorDist(lv,rv):
    return math.sqrt(sum(((l-r)**2 for l,r in zip(lv,rv))))

def matrixDist(LM,RM):
    return max([vectorDist(lr,rr) for lr,rr in zip(LM,RM)])

class SilvKeys_export_menu(Operator,ExportHelper):
    bl_idname = "custom_export.silv_keys_export_menu"
    bl_label = "Export VM"
    bl_description = "Exports VMs as SilvKeys"
    bl_options = {'REGISTER', 'PRESET'}

    filename_ext = ".tex"
    filter_glob = StringProperty(default="*.tex", options={'HIDDEN'}, maxlen=255)

    weld = BoolProperty(
            name = "Weld Vertices.",
            description = "Welds seams at Secondary UV level to avoid artifacting from seams",
            default = False
            )
    tolerance = FloatProperty(
            name = "Weld Distance",
            description = "Distance tolerancee for vertex welding",
            default = 0.0001
            )
    aggressive_optimization = BoolProperty(
            name = "Optimize Packing",
            description = "Aggresively Optimizes grouping of vertices based on delta similarity.",
            default = False,
            )
    account_normals = BoolProperty(
            name = "Account for Normals",
            description = "Account for Normals when Performing Delta Optimization.",
            default = False,
            )
    optimization_tolerance = FloatProperty(
            name = "Packing Tolerance",
            description = "Vector distance between deltas to group",
            default = 0.01,
            )
    secondary = BoolProperty(
            name = "Use current Secondary UV.",
            description = "Use current Secondary UV instead of gnerating a new one.",
            default = False
            )
    fullfloat = BoolProperty(
            name = "Full Float.",
            description = "Exports position as full floats instead of half floats",
            default = False
            )
    export_all = BoolProperty(default = False,
                              name = "Export Normals and Tangents",
                              description = "Produces matching Normal and Tangent VM.",
                              )
    normal_path = StringProperty(
                                 name = "Normal Map Path",
                                 description = "Path to Normal Output. Set to empty for it to mirror the position path.")
    tangent_path = StringProperty(
                                 name = "Tangent Map Path",
                                 description = "Path to Tangent Output. Set to empty for it to mirror the position path.")
    
    def invoke(self,context,event):
        if context.scene.mhw_silv_key_pos:
            self.filepath = context.scene.mhw_silv_key_pos            
        self.normal_path = context.scene.mhw_silv_key_nor
        self.tangent_path = context.scene.mhw_silv_key_tan
        return super().invoke(context,event)

    def execute(self,context):
        self.sanityCheck(context)        
        vertOrdering = self.generateVertexOrdering(context)
        deltas = self.compileDeltas(context,self.export_all)
        finalDeltas = self.summarizeDeltas(vertOrdering,deltas)
        pos = self.filepath
        if self.export_all:
            if not self.normal_path:
                nor =  resolveNorTanPath(self.filepath,0)
                if nor: self.normal_path = nor
            if not self.tangent_path:
                tan = resolveNorTanPath(self.filepath,1)
                if tan: self.tangent_path = tan  
        nor,tan = self.normal_path,self.tangent_path
        self.exportDeltas(finalDeltas,pos,nor,tan)
        return {'FINISHED'}

    def sanityCheck(self,context):
        scn = context.scene
        basis = scn.mhw_silv_keys[0].mesh.data
        l = len(basis.vertices)
        for mesh in scn.mhw_silv_keys[1:]:
            if l != len(mesh.mesh.data.vertices):
                raise VertexCountMismatch("SilvKeys have different vertex count to basis.")
        
    def compileDeltas(self,context,exportTanSpace):
        deltas = []
        meshes = [k.mesh for k in context.scene.mhw_silv_keys]
        posDeltas = compilePosDelta(meshes)
        deltas.append(posDeltas)
        if exportTanSpace:
            norDeltas,tanDeltas = compileNorTanDelta(meshes)
            deltas.append(norDeltas)
            deltas.append(tanDeltas)
        return deltas
    
    def exportDeltas(self,deltas,pos,nor,tan):
        for d,m,op in zip(deltas,
                          [pos,nor,tan],
                          [self.exportPosDelta,self.exportNorTanDelta,self.exportNorTanDelta]):
            op(d,m)            
    
    def exportPosDelta(self,deltas,outf):
        TexFile().construct(deltas, "Full_Pos_VM" if self.fullfloat else "Pos_VM").write(outf)
        
    def exportNorTanDelta(self,deltas,outf):
        TexFile().construct(deltas,"NorTan_VM").write(outf)
    
    def summarizeDeltas(self,vertOrdering,deltas):
        return list(map(lambda f: list(map(lambda x: reorderDelta(vertOrdering,x),f)),deltas))
    
    def getDoublesCluster(self,basis):
        clustering = ClusterSet()
        for ix,vert in enumerate(basis.vertices):
            clustering.new(ix,vert.co)
        clustering.reduce(self.tolerance)
        return clustering

    def updateMeshDoubles(self,keym,doublemap):
        clustering = self.getDoublesCluster(keym)
        doublemap.intersect(clustering)
        return doublemap
    
    def generateVertexOrdering(self,context):
        #self.aggresive_optimization = False
        scn = context.scene
        basis = scn.mhw_silv_keys[0].mesh
        if self.secondary:
            vertOrdering = getVertexOrderingList(basis)
        else:
            if self.weld:
                doublemap = self.removeDoublesOrdering(basis,scn.mhw_silv_keys[1:])
            elif self.aggressive_optimization:
                doublemap = self.violentOptimizeOrdering(scn.mhw_silv_keys) 
            else:
                doublemap = {}
            vertOrdering = self.orderingFromDoubleMap(basis,doublemap)        
        return vertOrdering                  

    def removeDoublesOrdering(self,basis,keys):
        doublemap = self.getDoublesCluster(basis.data)
        for key in keys:
            keymesh = key.mesh.data
            doublemap = self.updateMeshDoubles(keymesh,doublemap)
        doublemap.clean()
        return doublemap
    
    def generateDeltaCluster(self,deltas,rowIx):
        clustering = ClusterSet()
        for ix,vert in enumerate(deltas):
            clustering.new(ix,vert[rowIx])
        clustering.reduce(self.optimization_tolerance)
        return clustering
    
    
    def optimizeDeltaNors(self,keys):
        nors = [ [] for vert in keys[0].mesh.data.vertices ]
        for mdv in keys:
            mesh = mdv.mesh.data.vertices
            for nor,vert in zip(nors,mesh):
                nor.append(vert.normal.normalized())
        base = self.generateDeltaCluster(nors,0)
        #print(base.internalReferenceTable.keys())
        for i in range(1,len(keys)):
            cluster = self.generateDeltaCluster(nors,i)
            #print(cluster.internalReferenceTable.keys())
            base.intersect(cluster)
            base.clean()
            print("Normals Pass #%d: %d"%(i,len(base)))        
        return base
    
    def optimizeDeltaVerts(self,keys):
        verts = [ [] for vert in keys[0].mesh.data.vertices ]
        for l,r in zip(keys[:-1],keys[1:]):
            for arr,v0,v1 in zip(verts,l.mesh.data.vertices,r.mesh.data.vertices):
                arr.append(v1.co - v0.co)
                
        base = self.generateDeltaCluster(verts,0) 
        #print(base.internalReferenceTable.keys())
        for key in range(1,len(keys)-1):            
            print("Pass #%d: %d"%(key-1,len(base)))
            keyClustering = self.generateDeltaCluster(verts,key)
            #print(keyClustering.internalReferenceTable.keys())
            base.intersect(keyClustering)
            base.clean()   
        print("Pass #%d: %d"%(key,len(base)))        
        return base
    
    def violentOptimizeOrdering(self,keys):
        print("Exporting VM in Optimized Mode")
        base = self.optimizeDeltaVerts(keys)
        if self.account_normals:
            norbase = self.optimizeDeltaNors(keys)
        base.strong_intersect(norbase)
        base.clean()
        return base

    def orderingFromDoubleMap(self,basis,doublemap):
        autonumbering = 0
        reUV = []
        usedGroups = {}
        for ix,b in enumerate(basis.data.vertices):
            if ix in doublemap:
                if doublemap[ix].id in usedGroups:
                    reUV.append(usedGroups[doublemap[ix].id])
                else:
                    reUV.append(autonumbering)                    
                    usedGroups[doublemap[ix].id]=autonumbering
                    autonumbering += 1
            else:
                reUV.append(autonumbering)
                autonumbering += 1                
        createVertexOrderingUV(basis,reUV)
        return getVertexOrderingList(basis)
    
# =============================================================================
# Non Menu Access
# =============================================================================

class SilvKeys_import(SilvKeys_import_menu):
    bl_idname = "scene.silv_keys_import"
    bl_label = "Import VM"
    bl_description = "Imports VMs as SilvKeys"
    bl_options = {'REGISTER', 'UNDO'}
    
    import_all = BoolProperty(default = False,
                              name = "Import Normals and Tangents",
                              description = "Imports matching Normal and Tangent VM.",
                              options={"HIDDEN"}
                              )

    def invoke(self,context,event):
        self.filepath = context.scene.mhw_silv_key_pos            
        self.normal_path = context.scene.mhw_silv_key_nor
        self.tangent_path = context.scene.mhw_silv_key_tan
        return self.execute(context)

    @classmethod
    def poll(self,context):
        return context.object and context.object.type == "MESH" and len(context.object.data.uv_layers) > 1 and context.scene.mhw_silv_key_pos
    
class SilvKeys_export(SilvKeys_export_menu):
    bl_idname = "scene.silv_keys_export"
    bl_label = "Export VM (*VM.tex)"
    bl_description = "Exports VMs as SilvKeys"
    bl_options = {'REGISTER'}

    
    export_all = BoolProperty(default = False,
                              name = "Export Normals and Tangents",
                              description = "Produces matching Normal and Tangent VM.",
                              options={"HIDDEN"}
                              )
    weld = BoolProperty(
            name = "Weld Vertices.",
            description = "Welds seams at Secondary UV level to avoid artifacting from seams",
            default = False
            )
    tolerance = FloatProperty(
            name = "Weld Distance",
            description = "Distance tolerancee for vertex welding",
            default = 0.0001
            )
    aggressive_optimization = BoolProperty(
            name = "Optimize Packing",
            description = "Aggresively Optimizes grouping of vertices based on delta similarity.",
            default = False,
            )
    account_normals = BoolProperty(
            name = "Account for Normals",
            description = "Account for Normals when Performing Delta Optimization.",
            default = False,
            )
    optimization_tolerance = FloatProperty(
            name = "Packing Tolerance",
            description = "Vector distance between deltas to group",
            default = 0.01,
            )    
    secondary = BoolProperty(
            name = "Use current Secondary UV.",
            description = "Use current Secondary UV instead of gnerating a new one.",
            default = False
            )
    fullfloat = BoolProperty(
            name = "Full Float.",
            description = "Exports position as full floats instead of half floats",
            default = False
            )
    export_all = BoolProperty(default = False,
                              name = "Export Normals and Tangents",
                              description = "Produces matching Normal and Tangent VM.",
                              )
    
    def invoke(self,context,event):
        self.filepath = context.scene.mhw_silv_key_pos            
        self.normal_path = context.scene.mhw_silv_key_nor
        self.tangent_path = context.scene.mhw_silv_key_tan
        return self.execute(context)
    
    @classmethod
    def poll(self,context):
        return len(context.scene.mhw_silv_keys) > 1
        
def menu_func_import(self, context):
    self.layout.operator(SilvKeys_import_menu.bl_idname, text="MHW VM (VM.tex)")
def menu_func_export(self, context):
    self.layout.operator(SilvKeys_export_menu.bl_idname, text="MHW VM (VM.tex)")