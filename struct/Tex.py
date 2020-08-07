# -*- coding: utf-8 -*-
"""
Created on Tue Jun 16 06:45:55 2020

@author: AsteriskAmpersand
"""
from collections import OrderedDict
import sys
try:
    from ..common.Cstruct import PyCStruct
    from ..common.FileLike import FileLike
except:
    sys.path.insert(0, r'..\common')
    from Cstruct import PyCStruct
    from FileLike import FileLike
    
class Tex_Header(PyCStruct):
    fields = OrderedDict([
    		("TEXString","char[4]"),
    		("version","int64"),
    		("datablock","int32"),
    		("format","int32"),
    		("mipCount","int32"),
    		("width","int32"),
    		("height","int32"),
    		("ONE0","int32"),
    		("typeData","int32"),
    		("ONE1","int32"),
    		("NULL0","int32[3]"),
    		("NEG0","int32"),
    		("NULL1","int32[2]"),
    		("Special","int32"),
    		("NULL2","int32[4]"),
    		("NEG1","int32[8]"),
    		("Flags","byte[32]"),
    		("NULLX","int32[8]"),
    		("pixelOffset","int64"),
            ])
#flags:
#(8, 0, 0, 0, 8, 0, 8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 8, 0, 8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 8, 0, 8, 0), 
#(0, 8, 0, 0, 0, 8, 0, 8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 8, 0, 8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 8, 0, 8),
#(16, 0, 0, 0, 8, 0, 16, 0, 0, 0, 0, 0, 0, 0, 0, 0, 8, 0, 16, 0, 0, 0, 0, 0, 0, 0, 0, 0, 8, 0, 16, 0)
    defaultProperties = {
            "TEXString":"TEX",
            "version":0x10,
            "datablock":0,
            "format":2,            
            "mipCount":1,
            "ONE0":1,
            "ONE1":1,
            "NULL0":[0]*3,
            "NULL1":[0]*2,
            "NULL2":[0]*4,
            "NEG0":-1,
            "NEG1":[-1]*8,
            "NULLX":[-1]*8,
            "Special":1,
            "pixelOffset":0xC0,
            "Flags":(8, 0, 0, 0, 8, 0, 8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 8, 0, 8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 8, 0, 8, 0),
            }
    requiredProperties = {
            "width","height","typeData",
            }

class CVector(PyCStruct):
    def vector(self):
        return [(self.x,self.y,self.z)]
    requiredProperties = {"x","y","z"}
class FullVec(CVector):
    fields = OrderedDict([
    		("x","float"),
    		("y","float"),
    		("z","float"),
    		("w","float"),
            ])
    defaultProperties = {"w":1}
    
class ShapeVec(CVector):
    fields = OrderedDict([
    		("x","hfloat"),
    		("y","hfloat"),
    		("z","hfloat"),
    		("w","hfloat"),
            ])
    defaultProperties = {"w":1}

class NorTanVec(CVector):
    fields = OrderedDict([
    		("x","ubyte"),
    		("y","ubyte"),
    		("z","ubyte"),
    		("w","ubyte"),
            ])
    defaultProperties = {"w":255}
    def marshall(self,data):
        super().marshall(data)
        xyz = [self.x,self.y,self.z]
        #self.rawx, self.rawy, self.rawz = xyz.copy()
        #neg = min(enumerate(xyz), key=lambda x: (x[1]))[0]
        #neg = max(enumerate(xyz), key=lambda x: abs(x[1]))[0]#used to be without abs
        xyz = list(map(lambda x: x-128,xyz))
        #xyz[neg] *= -1
        self.x,self.y,self.z = xyz        
        return self
    def construct(self,data):   
        super().construct(data)
        self.w = 255
        return self

    
    @staticmethod
    def repack(x,y,z):
        xyz = [x,y,z]
        #with abs
        #i = min(enumerate(xyz), key=lambda x: abs(x[1]))[0]
        #xyz[i] *= -1
        #return xyz
        #without abs
        perms = []
        for i in range(3):
            w = xyz.copy()
            w[i]*=-1
            if w[i] <= w[(i+1)%3] and w[i] <= w[(i+2)%3]:
                #strict inequality should be used to manually disambiguate
                #perms.append(i) #this is used when disambiguating is needed
                return w
        xyz[perms[0]]*=-1
        return xyz
    
    def serialize(self):        
        xyz = [self.x,self.y,self.z]
        #xyz = self.repack(self.x,self.y,self.z)
        xyz = list(map(lambda x: x+128,xyz))
        return self.CStruct.serialize({"x":xyz[0],"y":xyz[1],"z":xyz[2],"w":255})
        #orderMake = lambda w: list(map(lambda x: x[0],sorted(enumerate(w),key = lambda x: x[1]))
        #ordering = orderMake(xyz)
        

class Dummy(PyCStruct):
    fields = OrderedDict([])
    
class TexFile():
    def __init__(self,filePath=None):
        if filePath is not None:
            with open(filePath,"rb") as inf:
                file = FileLike(inf.read())
            self.marshall(file)
    
    def marshall(self,data):
        self.Header = Tex_Header().marshall(data)
        typing = self.datatype(self.Header)
        self.Data = [[typing().marshall(data) for _ in range(self.Header.width)] for _ in range(self.Header.height)]
        return self
        
    def construct(self,data,typing):
        h = len(data)
        w = 0 if not h else len(data[0])
        typeKey = {"Full_Pos_VM":1,"Pos_VM":2,"NorTan_VM":7}[typing]
        typeData = {"Full_Pos_VM":FullVec,"Pos_VM":ShapeVec,"NorTan_VM":NorTanVec}[typing]
        self.Header = Tex_Header().construct({"width":w,"height":h,"typeData":typeKey})
        self.Data = [[typeData().construct({"x":px[0],"y":px[1],"z":px[2]}) for px in row] for row in data]
        return self
    
    def serialize(self):
        return self.Header.serialize()+b''.join([b''.join(map(lambda x: x.serialize(),row)) for row in self.Data])

    def write(self,path):
        with open(path,"wb") as outf:
            outf.write(self.serialize())
    
    def datatype(self,header):
        if header.Special != 1:
            print("Non-Special")
            return Dummy
        if header.Special == 1:
            if header.typeData == 7:
                return NorTanVec
            elif header.typeData == 2:
                return ShapeVec
            elif header.typeData == 1:
                return FullVec
    
    def __iter__(self):
        return iter(self.Data)
    
def writeDebugNormals(outf,normalPacks):
    with open(outf,"w") as outf:
        for pack in normalPacks:
            outf.write("\n")
            for n in pack:
                normal = Vector((n.rawx,n.rawy,n.rawz))
                outf.write("%d %d %d\n"%tuple(normal) )
    
if __name__ in "__main__":
    from pathlib import Path
    from mathutils import Vector
    
    t = TexFile(r"E:\MHW\chunkG0\vfx\mod\em\em127\md_em127_001\md_127_001_nor_VM.tex")
    writeDebugNormals(r"E:\MHW\chunkG0\vfx\mod\em\em127\md_em127_001\test.test",t.Data)
    raise
    s = {}
    for p in Path(r"E:\MHW\chunkG0").rglob("*VM.tex"):
        print(p)
        t = TexFile(p)
        if t.Header.typeData != 7:
            continue
        leniency = 0
        for k in t:
            for i,p0 in enumerate(k):
                try:
                    p1 = NorTanVec().marshall(FileLike(p0.serialize()))
                except:
                    print(i)
                    print(p0)
                    raise
                if p0 != p1:
                    raise ValueError
    #for k in s:
    #    print(k)
    #    for p in sorted(s[k],key=lambda x: eval(x.split(": ")[1])):
    #        print("\t%s"%p)