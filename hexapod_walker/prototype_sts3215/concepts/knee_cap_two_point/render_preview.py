"""Local geometric QA view, using generated meshes rather than a sketch."""
import math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib.colors import to_rgb
import make_variant as v

_, old = v.inputs()
new={k:v.trimesh.load_mesh(v.OUT/(k+".stl")) for k in (v.CAP_KEY,v.BODY_KEY)}
hw=v.hardware()
fig=plt.figure(figsize=(14,7),facecolor="#f5f7fa")
for col,explode in enumerate((0,16)):
    ax=fig.add_subplot(1,2,col+1,projection="3d")
    parts=[(v.transformed(new[v.BODY_KEY],np.linalg.inv(v.g.KNEE_CAP_TO_FEMUR)),"#7fb069")]
    cap=new[v.CAP_KEY].copy();cap.apply_translation([0,explode,0]);parts.append((cap,"#719fc7"))
    for x,z in v.CENTRES:
        nut=hw["knee_cap_nut"].copy();nut.apply_translation([x,12.55,z]);parts.append((nut,"#d2ab52"))
        s=v.transformed(hw["knee_cap_screw"],np.array(v.v7.placement(np.eye(4),[x,v.SEAT+explode,z],[0,-1,0])).reshape(4,4).T)
        parts.append((s,"#76818d"))
    for mesh,color in parts:
        light=np.array([-.4,.6,.8]);light/=np.linalg.norm(light)
        shade=.55+.45*np.maximum(0,mesh.face_normals@light)
        colors=np.clip(np.asarray(to_rgb(color))[None,:]*shade[:,None],0,1)
        ax.add_collection3d(Poly3DCollection(mesh.triangles,facecolors=colors,edgecolors="none",zsort="average"))
    ax.set_xlim(-42,39);ax.set_ylim(-20,43);ax.set_zlim(-12,46)
    ax.set_box_aspect([81,63,58]);ax.view_init(elev=23,azim=115)
    ax.set_axis_off();ax.set_title("Assembled: both screws from cap face" if not explode else "Cap lifted: side-entry captive nuts",fontsize=14,pad=4)
fig.suptitle("v34-derived knee-cap repair • M3×8 screws • M3 nuts under 3 mm retaining roofs",fontsize=15)
fig.subplots_adjust(left=0,right=1,bottom=0,top=.89,wspace=-.08)
fig.savefig(v.OUT/"preview.png",dpi=145,facecolor=fig.get_facecolor())
