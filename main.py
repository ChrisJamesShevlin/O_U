import tkinter as tk
import math
from math import comb

# --- Configuration ---
COMMISSION = 0.05  # 5% commission
# --- Utility Functions ---
def zip_probability(lam, k, p_zero=0.0):
    """Zero-inflated Poisson probability."""
    if k == 0:
        return p_zero + (1 - p_zero) * math.exp(-lam)
    return (1 - p_zero) * ((lam ** k) * math.exp(-lam)) / math.factorial(k)

def fair_odds(prob):
    return (1/prob) if prob > 0 else float('inf')

# --- Calculation Logic ---
def calculate_insights():
    try:
        getf = lambda k: float(entries[k].get()) if entries[k].get() else 0.0

        # --- Gather inputs ---
        home_avg_scored   = getf("entry_home_avg_scored")
        home_avg_conceded = getf("entry_home_avg_conceded")
        away_avg_scored   = getf("entry_away_avg_scored")
        away_avg_conceded = getf("entry_away_avg_conceded")
        home_xg           = getf("entry_home_xg")
        away_xg           = getf("entry_away_xg")
        home_xg_ag        = getf("entry_home_xg_against")
        away_xg_ag        = getf("entry_away_xg_against")
        balance           = getf("entry_account_balance")
        kelly_frac        = max(getf("entry_kelly_fraction")/100.0, 0.001)
        live_over         = getf("entry_live_over")  # pre-match Over 2.5 odds

        effective_balance = max(balance, 0)

        # --- Pre-match expected goals ---
        lam_h = home_xg
        lam_a = away_xg

        # --- Seasonal strength adjustments ---
        pm_h = home_avg_scored / max(0.75, away_avg_conceded)
        pm_a = away_avg_scored / max(0.75, home_avg_conceded)
        lam_h = 0.85 * lam_h + 0.15 * pm_h
        lam_a = 0.85 * lam_a + 0.15 * pm_a

        # --- Defensive quality adjustment ---
        lam_h *= 1 + (away_xg_ag - 1.0) * 0.1
        lam_a *= 1 + (home_xg_ag - 1.0) * 0.1

        # --- Bivariate Poisson PMF ---
        def biv_poisson_pmf(lh, la, lha, i, j):
            pmf = 0.0
            for k in range(min(i, j) + 1):
                term = (
                    math.exp(-(lh + la + lha)) *
                    (lh**(i-k) / math.factorial(i-k)) *
                    (la**(j-k) / math.factorial(j-k)) *
                    (lha**k / math.factorial(k))
                )
                pmf += term
            return pmf

        # covariance term (tunable fraction)
        lambda_ha = 0.05 * math.sqrt(lam_h * lam_a)

        # build joint distribution up to 10 goals each
        joint_probs = {
            (i, j): biv_poisson_pmf(lam_h, lam_a, lambda_ha, i, j)
            for i in range(11) for j in range(11)
        }
        total_mass = sum(joint_probs.values())
        if total_mass > 0:
            for key in joint_probs:
                joint_probs[key] /= total_mass

        # fair probability Over 2.5
        fair_over_prob = sum(p for (i, j), p in joint_probs.items() if i + j > 2)
        fair_over_odds = fair_odds(fair_over_prob)

        # --- Build output ---
        output = "=== Pre-Match Over Insights ===\n\n"
        output += f"Fair Pr(Over 2.5): {fair_over_prob*100:.1f}% (Fair Odds: {fair_over_odds:.2f})\n"
        output += f"Market Over Odds: {live_over:.2f}\n\n"

        # --- Back-value check (edge must exceed commission) ---
        edge_back = (live_over - fair_over_odds) / fair_over_odds
        if edge_back > COMMISSION:
            # EV per £1 staked after commission
            ev = fair_over_prob * (live_over - 1) * (1 - COMMISSION) - (1 - fair_over_prob)
            stake_back = effective_balance * kelly_frac * edge_back
            output += f"Back Over 2.5: EV {ev*100:.2f}%, Stake {stake_back:.2f}\n"
        else:
            output += "No back value on Over 2.5\n"

        # --- Lay-value check (edge must exceed commission) ---
        edge_lay = (fair_over_odds - live_over) / fair_over_odds
        if edge_lay > COMMISSION and live_over > 1:
            k = kelly_frac * edge_lay
            liability = effective_balance * k
            stake_lay = liability / (live_over - 1)
            output += f"Lay Over 2.5: Edge {edge_lay:.2%}, Liability {liability:.2f}, Stake {stake_lay:.2f}\n"
        else:
            output += "No lay value on Over 2.5\n"

        # --- Display results ---
        result_text.config(state="normal")
        result_text.delete("1.0", tk.END)
        for line in output.split("\n"):
            tag = (
                "insight" if line.startswith("===") else
                "lay"     if line.startswith("Lay") else
                "back"    if line.startswith("Back") else
                "normal"
            )
            result_text.insert(tk.END, line + "\n", tag)
        result_text.config(state="disabled")

    except Exception:
        result_text.config(state="normal")
        result_text.delete("1.0", tk.END)
        result_text.insert(tk.END, "Please enter valid numerical values.", "normal")
        result_text.config(state="disabled")

# --- Reset Function ---
def reset_all():
    for e in entries.values():
        e.delete(0, tk.END)
    result_text.config(state="normal")
    result_text.delete("1.0", tk.END)
    result_text.config(state="disabled")

# --- GUI Setup ---
root = tk.Tk()
root.title("Odds Apex - Over/Under")

main = tk.Frame(root)
main.pack(padx=10, pady=10)

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

for i, (key, label) in enumerate(zip(entries, labels)):
    tk.Label(main, text=label).grid(row=i, column=0, sticky="e", padx=5, pady=2)
    entries[key].grid(row=i, column=1, padx=5, pady=2)

# result text box
res_frame = tk.Frame(main)
res_frame.grid(row=len(entries), column=0, columnspan=2, pady=10)
result_text = tk.Text(res_frame, wrap=tk.WORD, bg="white", height=10)
result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
tk.Scrollbar(res_frame, command=result_text.yview).pack(side=tk.RIGHT, fill=tk.Y)
result_text.config(yscrollcommand=lambda *a: None)
result_text.config(state="disabled")

# Buttons
tk.Button(main, text="Calculate Over Insights", command=calculate_insights) \
    .grid(row=len(entries)+1, column=0, columnspan=2, pady=5)
tk.Button(main, text="Reset All", command=reset_all) \
    .grid(row=len(entries)+2, column=0, columnspan=2, pady=5)

# Tag styling
result_text.tag_configure("insight", foreground="green")
result_text.tag_configure("back",     foreground="blue")
result_text.tag_configure("lay",      foreground="red")
result_text.tag_configure("normal",   foreground="black")

root.mainloop()
