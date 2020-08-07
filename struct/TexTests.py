# -*- coding: utf-8 -*-
"""
Created on Thu Jun 18 19:27:17 2020

@author: AsteriskAmpersand
"""


from mathutils import Vector

f0 = r"E:\MHW\chunkG0\vfx\mod\em\em127\md_em127_001\test.test"
f1 = r"E:\MHW\chunkG0\vfx\mod\em\em127\md_em127_001\blenderPartialTest.test"
f2 = r"E:\MHW\chunkG0\vfx\mod\em\em127\md_em127_001\blendertest.test"


def testAngles(l,r):
    angle = l.angle(r)
    amin = -1
    for i in range(3):
        w = l.copy()
        w[i]*=-1
        if w.angle(r) < angle:
            amin = i
            angle = w.angle(r)
    return amin

def compareNormalFiles(f0,f1,f2):
    with open(f0,"r") as inf0, open(f1,"r") as inf1, open(f2,"r") as inf2:
        for n0,n1,n2 in zip(inf0,inf1,inf2):
            if len(n0) <4:
                continue
            x0,y0,z0 = map(int,n0.split(" "))
            x1,y1,z1 = map(int,n1.split(" "))
            x2,y2,z2 = map(int,n2.split(" "))
            a,b,c = Vector((x0,y0,z0)),Vector((x1,y1,z1)),Vector((x2,y2,z2))
            v = Vector((128,128,128))
            a -= v
            b -= v
            c -= v
            a.normalize(),b.normalize(),c.normalize()
            try:
                i = testAngles(a,c)
            except:
                print(a)
                print(c)
                raise
            #o = octant(a)
            mindex = min(enumerate(a),key = lambda x: x[1])[0]
            print("%d|%d - %03d %03d %03d/%03d %03d %03d"%(i,mindex,*(a*127),*(c*127)))
            
compareNormalFiles(f0,f1,f2)