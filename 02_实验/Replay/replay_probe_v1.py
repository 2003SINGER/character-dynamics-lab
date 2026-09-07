"""Small, auditable conditional linear probe trainer (Python/scipy).

The caller supplies frozen feature vectors, one candidate set per row, and the
gold index.  No source, scene, transition, or appraisal structure is learned.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
from scipy.optimize import minimize

PROBE_VERSION = "replay-linear-probe-v1"
LAMBDA_GRID = (1e-4, 1e-3, 1e-2, 1e-1, 1.0)

def _design(rows, means=None, scales=None):
    sets, ys = [], []
    all_x = np.asarray([x for row in rows for x in row["features"]], dtype=float)
    if means is None: means = all_x.mean(0)
    if scales is None: scales = all_x.std(0); scales = np.where(scales == 0, 1.0, scales)
    for row in rows:
        x = (np.asarray(row["features"], dtype=float) - means) / scales
        sets.append(x); ys.append(int(row["gold_index"]))
    return sets, np.asarray(ys), means, scales

def fit_stateful(rows, l2, means=None, scales=None):
    sets, ys, means, scales = _design(rows, means, scales)
    states = [float(r["state"]) for r in rows]; d = sets[0].shape[1]
    def fg(q):
        loss = 0.0; g = np.zeros_like(q)
        for x, s, y in zip(sets, states, ys):
            logits = x @ q[:d] + s * (x @ q[d:]); logits -= logits.max()
            p = np.exp(logits); p /= p.sum(); target = np.zeros(len(p)); target[y] = 1
            loss -= np.log(max(p[y], 1e-300)); g[:d] += (p-target) @ x; g[d:] += s * ((p-target) @ x)
        loss = loss / len(sets) + 0.5*l2*np.dot(q,q); g = g/len(sets) + l2*q
        return loss, g
    history=[]
    def cb(q):
        obj, grad=fg(q); reg=0.5*l2*np.dot(q,q); data=obj-reg; history.append({"iteration":len(history)+1,"objective":float(obj),"data_nll":float(data),"l2_penalty":float(reg),"gradient_norm":float(np.linalg.norm(grad)),"theta_norm":float(np.linalg.norm(q[:d])),"w_norm":float(np.linalg.norm(q[d:]))})
    result = minimize(lambda q: fg(q), np.zeros(2*d), jac=True, method="L-BFGS-B", callback=cb, options={"maxiter":1000,"gtol":1e-8})
    obj, grad=fg(result.x); data_nll=obj-0.5*l2*np.dot(result.x,result.x)
    return {"probe_version":PROBE_VERSION,"weights_theta":result.x[:d].tolist(),"weights_w":result.x[d:].tolist(),"lambda":l2,"means":means.tolist(),"scales":scales.tolist(),"optimization_history":history,"optimizer":{"method":"L-BFGS-B","max_iter":1000,"gtol":1e-8,"initialization":"zeros","deterministic":True,"success":bool(result.success),"status":int(result.status),"message":str(result.message),"iterations":int(result.nit),"function_evaluations":int(result.nfev),"gradient_evaluations":int(getattr(result,'njev',-1)),"final_objective":float(obj),"final_data_nll":float(data_nll),"final_l2_penalty":float(obj-data_nll),"final_gradient_norm":float(np.linalg.norm(grad))}}

def fit_no_state(rows, l2, means=None, scales=None):
    sets, ys, means, scales = _design(rows, means, scales); d=sets[0].shape[1]
    def fg(theta):
        loss=0.0; g=np.zeros_like(theta)
        for x,y in zip(sets,ys):
            z=x@theta; z-=z.max(); p=np.exp(z); p/=p.sum(); target=np.zeros(len(p)); target[y]=1
            loss-=np.log(max(p[y],1e-300)); g+=(p-target)@x
        return loss/len(sets)+0.5*l2*np.dot(theta,theta), g/len(sets)+l2*theta
    history=[]
    def cb(q):
        obj, grad=fg(q); reg=0.5*l2*np.dot(q,q); data=obj-reg; history.append({"iteration":len(history)+1,"objective":float(obj),"data_nll":float(data),"l2_penalty":float(reg),"gradient_norm":float(np.linalg.norm(grad)),"theta_norm":float(np.linalg.norm(q)),"w_norm":0.0})
    result=minimize(lambda q: fg(q), np.zeros(d), jac=True, method="L-BFGS-B", callback=cb, options={"maxiter":1000,"gtol":1e-8})
    obj, grad=fg(result.x); data_nll=obj-0.5*l2*np.dot(result.x,result.x)
    return {"probe_version":PROBE_VERSION,"weights_theta":result.x.tolist(),"weights_w":[0.0]*d,"lambda":l2,"means":means.tolist(),"scales":scales.tolist(),"optimization_history":history,"optimizer":{"method":"L-BFGS-B","max_iter":1000,"gtol":1e-8,"initialization":"zeros","deterministic":True,"success":bool(result.success),"status":int(result.status),"message":str(result.message),"iterations":int(result.nit),"function_evaluations":int(result.nfev),"gradient_evaluations":int(getattr(result,'njev',-1)),"final_objective":float(obj),"final_data_nll":float(data_nll),"final_l2_penalty":float(obj-data_nll),"final_gradient_norm":float(np.linalg.norm(grad))}}

def predict(model, features, state):
    x=(np.asarray(features,float)-np.asarray(model["means"]))/np.asarray(model["scales"]); q=np.asarray(model["weights_theta"])+float(state)*np.asarray(model["weights_w"]); z=x@q; z-=z.max(); p=np.exp(z); return (p/p.sum()).tolist()

def evaluate(model, rows, state_override=None):
    nll=0.0
    for row in rows:
        p=predict(model, row["features"], row.get("state", 0.0) if state_override is None else state_override(row))
        nll -= np.log(max(p[int(row["gold_index"])], 1e-300))
    return nll / len(rows)

if __name__ == "__main__":
    raise SystemExit("library module; use fit_stateful from a frozen train/validation split")
