import importlib.util
from pathlib import Path
import numpy as np
import pytest
P=Path(__file__).with_name("probe_support_yaw.py")
spec=importlib.util.spec_from_file_location("support_assay_tested",P)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def setup_geometry():
    p=np.array([[.2,0,0],[.1,.15,0],[-.1,.15,0],[-.2,0,0],[-.1,-.15,0],[.1,-.15,0]])
    load=np.array([5.,0.,5.,0.,5.,0.])
    jac=np.repeat(np.eye(3)[None,:,:]*.1,6,axis=0)
    return p,load,jac,np.zeros(3)

def test_sign_symmetry_and_stance_tangent_without_template():
    args=setup_geometry()
    pos,meta=m.geometric_direction(*args,.15)
    neg,negmeta=m.geometric_direction(*args,-.15)
    assert meta["available"] and negmeta["available"]
    np.testing.assert_array_equal(pos,-neg)
    assert np.max(np.abs(pos))==pytest.approx(.05)
    np.testing.assert_array_equal(pos.reshape(6,3)[[1,3,5]],0)
    b=-np.cross([0,0,1],args[0][[0,2,4]])
    executed=np.einsum("ijk,ik->ij",args[2][[0,2,4]],pos.reshape(6,3)[[0,2,4]])
    scales=(executed*b).sum(1)/(b*b).sum(1)
    assert np.all(scales>0)
    np.testing.assert_allclose(executed,scales[:,None]*b,atol=1e-15)

def test_world_yaw_rotation_covariance():
    p,load,jac,origin=setup_geometry()
    theta=.71;R=np.array([[np.cos(theta),-np.sin(theta),0],[np.sin(theta),np.cos(theta),0],[0,0,1]])
    a,_=m.geometric_direction(p,load,jac,origin,.15)
    b,_=m.geometric_direction(p@R.T,load,np.einsum("ij,njk->nik",R,jac),R@origin,.15)
    np.testing.assert_allclose(a,b,atol=1e-15)

def test_support_and_leg_rank_unavailable_not_replaced():
    p,load,jac,origin=setup_geometry()
    load[4]=.5
    v,meta=m.geometric_direction(p,load,jac,origin,.15)
    assert meta["reason"]=="fewer_than_three_support_feet";assert not np.any(v)
    load[4]=5
    p[:,1]=0
    v,meta=m.geometric_direction(p,load,jac,origin,.15)
    assert meta["reason"]=="support_rank_below_two";assert not np.any(v)
    p,load,jac,origin=setup_geometry()
    jac[2,2,2]=0
    v,meta=m.geometric_direction(p,load,jac,origin,.15)
    assert meta["reason"]=="leg_2_rank_below_three";assert not np.any(v)

def test_cutoff_strict_and_nonfinite_fail_closed():
    *_,keep,cut=m.fixed_svd(np.diag([1.,1.,1e-6]))
    assert cut==1e-6 and keep.sum()==2
    p,load,jac,origin=setup_geometry();jac[2,0,0]=np.nan
    v,meta=m.geometric_direction(p,load,jac,origin,.15)
    assert meta["reason"]=="nonfinite_geometry";assert not np.any(v)

def test_zero_command_uses_no_geometry_and_no_hidden_schedule():
    v,meta=m.geometric_direction(None,None,None,None,0)
    assert not np.any(v) and meta["reason"]=="zero_command"

def test_original_retention_boundaries():
    b=dict(valid=True,fwd_disp_m=1,loaded_slip_m=1,max_abs_roll_deg=2,
        max_abs_pitch_deg=2,window_ticks=80,terminated_in_window=False,nonwalk_ticks=0)
    good=dict(b,fwd_disp_m=.9,loaded_slip_m=1.25,max_abs_roll_deg=5,max_abs_pitch_deg=5)
    assert m.retention(good,b)
    for changed in [dict(good,fwd_disp_m=.899),dict(good,loaded_slip_m=1.251),
                    dict(good,max_abs_pitch_deg=5.01),dict(good,terminated_in_window=True),
                    dict(good,nonwalk_ticks=1),dict(good,window_ticks=79)]:
        assert not m.retention(changed,b)

def test_real_robot_abs_conversion_and_mujoco_jacobian_chain_rule():
    import mujoco
    path=Path(__file__).resolve().parents[3]/"hexapod_walker/prototype_sts3215/hexapod_core/joint_frame.py"
    spec=importlib.util.spec_from_file_location("actual_joint_frame",path)
    frame=importlib.util.module_from_spec(spec);spec.loader.exec_module(frame)
    class Env:
        _logical_to_mujoco_q=staticmethod(frame.robot_abs_rad_to_mujoco_rel_rad)
    logical=np.tile([.2,.4,1.2],6)
    C=m.joint_conversion(Env(),logical)
    block=np.array([[1.,0.,0.],[0.,1.,0.],[0.,-1.,1.]])
    np.testing.assert_allclose(C,np.kron(np.eye(6),block),atol=1e-14)
    assert abs(C[2,1])==pytest.approx(1.)
    xml="""<mujoco><worldbody><body name="yaw">
      <joint name="q0" axis="0 0 1"/><geom type="sphere" size=".01"/>
      <body name="hip" pos=".08 0 0"><joint name="q1" axis="0 1 0"/>
      <geom type="sphere" size=".01"/>
      <body name="knee" pos=".10 0 0"><joint name="q2" axis="0 1 0"/>
      <geom type="sphere" size=".01"/><site name="foot" pos=".12 0 0"/>
      </body></body></body></worldbody></mujoco>"""
    model=mujoco.MjModel.from_xml_string(xml);data=mujoco.MjData(model)
    data.qpos[:]=frame.robot_abs_rad_to_mujoco_rel_rad(logical)[:3]
    mujoco.mj_forward(model,data)
    J=np.zeros((3,model.nv));Jr=np.zeros_like(J)
    mujoco.mj_jacSite(model,data,J,Jr,model.site("foot").id)
    scale=np.diag([.4,.7,.9]);analytic=J@C[:3,:3]@scale
    eps=1e-7;numeric=np.zeros((3,3))
    for j in range(3):
        positions=[]
        for sign in (1,-1):
            perturbed=logical.copy();perturbed[j]+=sign*eps*scale[j,j]
            scratch=mujoco.MjData(model)
            scratch.qpos[:]=frame.robot_abs_rad_to_mujoco_rel_rad(perturbed)[:3]
            mujoco.mj_kinematics(model,scratch)
            positions.append(scratch.site_xpos[model.site("foot").id].copy())
        numeric[:,j]=(positions[0]-positions[1])/(2*eps)
    np.testing.assert_allclose(analytic,numeric,atol=1e-9,rtol=1e-7)
    assert np.linalg.norm(J@scale-numeric)>1e-3
