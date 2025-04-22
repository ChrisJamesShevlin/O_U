import tkinter as tk
import math

# --- Configuration ---
COMMISSION = 0.05      # 5% commission
EDGE_THRESHOLD = 0.05  # 5% minimum edge
EV_THRESHOLD = 0.02    # 2% minimum EV

# --- Utility Functions ---
def zip_probability(lam, k, p_zero=0.0):
    """Zero‑inflated Poisson probability."""
    if k == 0:
        return p_zero + (1 - p_zero) * math.exp(-lam)
    return (1 - p_zero) * ((lam ** k) * math.exp(-lam)) / math.factorial(k)

def fair_odds(prob):
    return (1 / prob) if prob > 0 else float('inf')

# --- Calculation Logic ---
def calculate_insights():
    try:
        getf = lambda k: float(entries[k].get()) if entries[k].get() else 0.0

        # inputs
        home_avg_scored   = getf("entry_home_avg_scored")
        home_avg_conceded = getf("entry_home_avg_conceded")
        away_avg_scored   = getf("entry_away_avg_scored")
        away_avg_conceded = getf("entry_away_avg_conceded")
        home_xg           = getf("entry_home_xg")
        away_xg           = getf("entry_away_xg")
        home_xg_ag        = getf("entry_home_xg_against")
        away_xg_ag        = getf("entry_away_xg_against")
        balance           = getf("entry_account_balance")
        kelly_frac        = max(getf("entry_kelly_fraction") / 100.0, 0.001)
        live_over         = getf("entry_live_over")
        eff_bal           = max(balance, 0)

        # expected goals adjustments
        lam_h = 0.85 * home_xg + 0.15 * (home_avg_scored / max(0.75, away_avg_conceded))
        lam_a = 0.85 * away_xg + 0.15 * (away_avg_scored / max(0.75, home_avg_conceded))
        lam_h *= 1 + (away_xg_ag - 1.0) * 0.1
        lam_a *= 1 + (home_xg_ag - 1.0) * 0.1

        # bivariate Poisson PMF
        def biv(lh, la, lha, i, j):
            s = 0.0
            for k in range(min(i, j) + 1):
                s += math.exp(-(lh + la + lha)) * \
                     (lh**(i-k)/math.factorial(i-k)) * \
                     (la**(j-k)/math.factorial(j-k)) * \
                     (lha**k/math.factorial(k))
            return s

        cov = 0.05 * math.sqrt(lam_h * lam_a)
        joint = {(i, j): biv(lam_h, lam_a, cov, i, j)
                 for i in range(11) for j in range(11)}
        total = sum(joint.values())
        if total > 0:
            for key in joint:
                joint[key] /= total

        fair_p_over = sum(p for (i, j), p in joint.items() if i + j > 2)
        fair_o = fair_odds(fair_p_over)

        out = []
        out.append("=== Pre‑Match Over Insights ===\n")
        out.append(f"Fair Pr(Over 2.5): {fair_p_over*100:.1f}%  (Fair Odds: {fair_o:.2f})")
        out.append(f"Market Odds Over 2.5: {live_over:.2f}\n")

        # Back side
        edge_back = (live_over - fair_o) / fair_o
        ev_back   = fair_p_over * (live_over - 1) * (1 - COMMISSION) - (1 - fair_p_over)
        if edge_back > EDGE_THRESHOLD and ev_back > EV_THRESHOLD:
            stake = eff_bal * kelly_frac * edge_back
            profit = stake * (live_over - 1) * (1 - COMMISSION)
            out.append(
                f"Back Over 2.5 → Edge {edge_back*100:.2f}%, "
                f"EV {ev_back*100:.2f}%, Stake {stake:.2f}, Profit {profit:.2f}"
            )
        else:
            out.append("No back value on Over 2.5")

        # Lay side
        edge_lay = (fair_o - live_over) / fair_o
        ev_lay   = (1 - fair_p_over) * (1 - COMMISSION) - fair_p_over * (live_over - 1)
        if live_over > 1 and edge_lay > EDGE_THRESHOLD and ev_lay > EV_THRESHOLD:
            kelly_k   = kelly_frac * edge_lay
            liability = eff_bal * kelly_k
            stake_lay = liability / (live_over - 1)
            out.append(
                f"Lay Over 2.5 → Edge {edge_lay*100:.2f}%, "
                f"EV {ev_lay*100:.2f}%, Liability {liability:.2f}, Stake {stake_lay:.2f}"
            )
        else:
            out.append("No lay value on Over 2.5")

        # Display
        result_text.config(state="normal")
        result_text.delete("1.0", tk.END)
        for line in out:
            tag = (
                "insight" if line.startswith("===") else
                "back"    if line.startswith("Back") else
                "lay"     if line.startswith("Lay") else
                "normal"
            )
            result_text.insert(tk.END, line + "\n", tag)
        result_text.config(state="disabled")

    except Exception:
        result_text.config(state="normal")
        result_text.delete("1.0", tk.END)
        result_text.insert(tk.END, "Please enter valid numerical values.", "normal")
        result_text.config(state="disabled")


def reset_all():
    for e in entries.values():
        e.delete(0, tk.END)
    result_text.config(state="normal")
    result_text.delete("1.0", tk.END)
    result_text.config(state="disabled")


# --- GUI Setup (unchanged) ---
root = tk.Tk(); root.title("Odds Apex - Over/Under")
main = tk.Frame(root); main.pack(padx=10, pady=10)

entries = {
    "entry_home_avg_scored":   tk.Entry(main),
    "entry_home_avg_conceded": tk.Entry(main),
    "entry_away_avg_scored":   tk.Entry(main),
    "entry_away_avg_conceded": tk.Entry(main),
    "entry_home_xg":           tk.Entry(main),
    "entry_away_xg":           tk.Entry(main),
    "entry_home_xg_against":   tk.Entry(main),
    "entry_away_xg_against":   tk.Entry(main),
    "entry_account_balance":   tk.Entry(main),
    "entry_kelly_fraction":    tk.Entry(main),
    "entry_live_over":         tk.Entry(main),
}

labels = [
    "Home Avg Goals Scored",  "Home Avg Goals Conceded",
    "Away Avg Goals Scored",  "Away Avg Goals Conceded",
    "Home xG",                "Away xG",
    "Home xG Against",        "Away xG Against",
    "Account Balance",        "Kelly Fraction (%)",
    "Live Odds Over 2.5"
]

for i, (k, lab) in enumerate(zip(entries, labels)):
    tk.Label(main, text=lab).grid(row=i, column=0, sticky="e", padx=5, pady=2)
    entries[k].grid(row=i, column=1, padx=5, pady=2)

res_frame = tk.Frame(main)
res_frame.grid(row=len(entries), column=0, columnspan=2, pady=10)
result_text = tk.Text(res_frame, wrap=tk.WORD, bg="white", height=10)
result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
tk.Scrollbar(res_frame, command=result_text.yview).pack(side=tk.RIGHT, fill=tk.Y)
result_text.config(yscrollcommand=lambda *a: None, state="disabled")

tk.Button(main, text="Calculate Over Insights", command=calculate_insights)\
    .grid(row=len(entries)+1, column=0, columnspan=2, pady=5)
tk.Button(main, text="Reset All", command=reset_all)\
    .grid(row=len(entries)+2, column=0, columnspan=2, pady=5)

for tag, color in [("insight","green"),("back","blue"),("lay","red"),("normal","black")]:
    result_text.tag_configure(tag, foreground=color)

root.mainloop()
