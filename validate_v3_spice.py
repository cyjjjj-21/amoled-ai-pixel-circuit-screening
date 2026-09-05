#!/usr/bin/env python3
"""Run ngspice behavioral source-disturbance benches for the V3 shortlist.

DTFT: uncalibrated square-law behavioral current source with VDS triode region.
SWT: voltage-controlled resistors. OLED: prescribed anode disturbance voltage.
No PDK, OLED electro-optics, or measured IGZO compact model is implied.
"""
import csv
import itertools
import json
import re
import subprocess
from pathlib import Path

from screen_v3 import OUT, TECH, dump_csv, timing_sweep


def pwl(intervals, stop):
    points = [(0., 0.)]
    for start, end in intervals:
        if start == 0:
            points[0] = (0., 4.)
        else:
            points.extend([(start, 0.), (start + .002, 4.)])
        points.extend([(end, 4.), (end + .002, 0.)])
    points.append((stop, 0.))
    return "PWL(" + " ".join(f"{t:.12g}u {v:g}" for t, v in points) + ")"


def netlist(row, timing, vth, beta=1., trace=False, parasitic=True):
    reset = timing["reset_us"]
    ce = reset + timing["comp_us"]
    ps = ce + timing["break_comp_prep_us"]
    pe = ps + timing["prep_us"]
    ws = pe + timing["break_prep_write_us"]
    we = ws + timing["write_us"]
    es = we + timing["break_write_emit_us"]
    stop = es + 16680.
    switches = dict(zip(("GREF", "XANCHOR", "DATA", "SCLAMP", "EM"), row["reference_mix"].split("/")))
    anchor_end = pe if row["track_prep"] else ce
    # SCLAMP stays on during write dead-time; it opens before EM to avoid a
    # VINIT-to-forced-anode short. GREF always opens before source relocation.
    waveforms = {
        "GC": [(0., ce)], "XC": [(0., anchor_end)],
        "SC": [(0., reset-.005), (ps, es-.005)],
        "DC": [(ws, we)], "EC": [(es, stop-.005)],
    }
    title = f"V3 source-disturbance bench {row['candidate_id']} VTH={vth} beta={beta}"
    lines = [title, "* Uncalibrated behavioral proxy; source voltage is prescribed, not an OLED model.",
             ".option reltol=1e-6 abstol=1e-16 vntol=1e-9 method=gear",
             "VVDD VDD 0 8", "VREF VREF 0 3", "VINIT VINIT 0 0", "VDATA VDATA 0 1.5",
             f"VOA OLED_A 0 PWL(0 1 {es+10:g}u 1 {es+10.02:g}u 1.5 {stop:g}u 1.5)",
             f".param vt={vth} beta={beta}u",
             "BDRT VDD S I={beta*(max(V(G,S)-vt,0)*min(max(V(VDD,S),0),max(V(G,S)-vt,0))-0.5*min(max(V(VDD,S),0),max(V(G,S)-vt,0))^2)}",
             f"CST G S {row['c1_ff']:g}f", f"CDATA G X {row['c2_ff']:g}f"]
    lines += [f"CPG G 0 {3 if parasitic else 0.000001}f", "CPS S 0 20f", f"CPX X 0 {2 if parasitic else 0.000001}f"]
    for role, (a, b, control) in {
        "GREF": ("G", "VREF", "GC"), "XANCHOR": ("X", "S", "XC"),
        "DATA": ("X", "VDATA", "DC"), "SCLAMP": ("S", "VINIT", "SC"),
        "EM": ("S", "OLED_A", "EC"),
    }.items():
        tech = TECH[switches[role]]
        lines += [f"S{role} {a} {b} {control} 0 MOD_{role}",
                  f".model MOD_{role} SW(Ron={tech['ron_ohm']} Roff={1/tech['goff_s']} Vt=2 Vh=0)"]
    for control, intervals in waveforms.items():
        lines.append(f"V{control} {control} 0 {pwl(intervals, stop)}")
    lines += ["BVGS VGS 0 V=V(G)-V(S)", "BU U 0 V=V(G)-V(S)-vt",
              f".tran .1u {stop:g}u 0 .2u",
              f".meas tran vgs_comp FIND V(VGS) AT={ce-.01:g}u",
              f".meas tran vgs_write FIND V(VGS) AT={we-.003:g}u",
              f".meas tran vgs_early FIND V(VGS) AT={es+5:g}u",
              f".meas tran vgs_before FIND V(VGS) AT={es+9:g}u",
              f".meas tran vgs_after FIND V(VGS) AT={es+11:g}u",
              f".meas tran source_before FIND V(S) AT={es+9:g}u",
              f".meas tran source_after FIND V(S) AT={es+11:g}u",
              f".meas tran vgs_end FIND V(VGS) AT={es+16660:g}u",
              f".meas tran overdrive FIND V(U) AT={es+5:g}u"]
    if trace:
        lines += [".control", "run", "set wr_singlescale", "set wr_vecnames",
                  "wrdata trace_full.txt V(G) V(S) V(X) V(VGS) V(GC) V(XC) V(SC) V(DC) V(EC)", ".endc"]
    lines += [".end", ""]
    return "\n".join(lines)


def main():
    directory = OUT / "spice"
    directory.mkdir(exist_ok=True)
    summary = json.loads((OUT / "summary.json").read_text())
    timings = {t["timing_id"]: t for t in timing_sweep()}
    rows = []
    for rank, row in enumerate(summary["top10"], 1):
        for vth, beta in itertools.product((-.5, .5, 1.5), (.1, 1., 10.)):
            stem = f"rank{rank:02}_vt{vth:g}_beta{beta:g}"
            path = directory / f"{stem}.cir"
            trace = rank == 1 and vth == .5 and beta == 1.
            path.write_text(netlist(row, timings[row["reference_timing"]], vth, beta, trace=trace))
            run = subprocess.run(["ngspice", "-b", path.name], cwd=directory,
                                 capture_output=True, text=True, timeout=60)
            output = "\n".join(line.rstrip() for line in
                               (run.stdout + run.stderr).splitlines()).rstrip() + "\n"
            (directory / f"{stem}.log").write_text(output)
            measures = {name: float(value) for name, value in re.findall(
                r"^\s*(vgs_\w+|source_\w+|overdrive)\s*=\s*([-+\d.eE]+)", output, re.M)}
            if len(measures) != 9 or run.returncode != 0:
                raise RuntimeError(f"Incomplete ngspice run: {stem}, measures={measures}, code={run.returncode}")
            sensitivity = abs((measures["vgs_after"]-measures["vgs_before"])/(measures["source_after"]-measures["source_before"]))
            rows.append({"rank": rank, "parameter_id": row["candidate_id"], "timing_id": row["reference_timing"],
                         "vth": vth, "beta_uav2": beta, **measures,
                         "source_sensitivity": sensitivity,
                         "hold_delta_vgs_mv": (measures["vgs_end"]-measures["vgs_after"])*1000,
                         "netlist": path.name})
        print(f"ngspice rank {rank}/10: 9 scenarios completed", flush=True)
    dump_csv(OUT / "spice_validation.csv", rows)
    # Bound the public trace size while retaining dense switching neighborhoods.
    import numpy as np
    trace = np.loadtxt(directory / "trace_full.txt", skiprows=1)
    keep = (trace[:, 0] < .00016)
    keep[::100] = True
    np.savetxt(directory / "trace_sampled.csv", trace[keep], delimiter=",",
               header="time_s,vg,vs,vx,vgs,gc,xc,sc,dc,ec", comments="")
    (OUT / "spice_run.json").write_text(json.dumps({"completed": len(rows), "PDK_runs": 0,
        "simulator": "ngspice", "model": "uncalibrated square-law DTFT; resistive SWT; forced OLED anode",
        "vth_scenarios": [-.5,.5,1.5], "beta_uav2_scenarios": [.1,1,10],
        "source_step_v": .5, "hold_ms": 16.66, "top10_reoptimized_after_spice": False}, indent=2))


if __name__ == "__main__":
    main()
