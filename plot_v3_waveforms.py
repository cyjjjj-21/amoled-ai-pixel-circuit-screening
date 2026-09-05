"""Plot actual sampled ngspice waveform data without synthesizing curve points."""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from screen_v3 import OUT


def main():
    data = np.loadtxt(OUT / "spice/trace_sampled.csv", delimiter=",", skiprows=1)
    time = data[:, 0] * 1e6
    plt.rcParams.update({"font.family":"DejaVu Sans", "font.size":10, "mathtext.fontset":"dejavusans"})
    fig, axes = plt.subplots(3, 1, figsize=(10, 8), layout="constrained")
    for ax, (left, right), title in zip(axes[:2], [(0,140),(128.45,129.1)],
                                       ["Programming and early emission", "COMP to PREP to WRITE to EMIT"]):
        mask = (time>=left)&(time<=right)
        for column, name, color, style in [(1,r"$V_G$","#315d78","-"),(2,r"$V_S$","#777777","--"),(4,r"$V_{GS}$","#a46a3b","-")]:
            ax.plot(time[mask], data[mask,column], label=name, color=color, linestyle=style, lw=1.6)
        ax.set(xlim=(left,right), ylabel="Voltage (V)", xlabel="Time (us)", title=title)
        ax.legend(loc="upper right",ncol=3,frameon=False)
    mask=(time>=138.75)&(time<=139.05)
    baseline=data[mask,4][0]
    axes[2].plot(time[mask],1000*(data[mask,4]-baseline),color="#315d78",lw=1.8)
    axes[2].set(xlim=(138.75,139.05),xlabel="Time (us)",ylabel=r"$\Delta V_{GS}$ (mV)",title="Response to a +0.5 V source step")
    for ax in axes:
        ax.spines[["top","right"]].set_visible(False)
        ax.grid(axis="y",alpha=.15)
    fig.suptitle("Rank 1: CST / CDATA = 640 / 20 fF; VTH = 0.5 V; beta = 1 uA/V^2",fontsize=13)
    fig.savefig(OUT / "waveforms.png",dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()
