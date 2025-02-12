import streamlit as st
import pandas as pd

st.set_page_config(page_title="LOI Checker 8000 Pro", layout="centered")

def calculate_incremental_rates(loan_amount, start_rate, steps=10):
    results = []
    current_rate = start_rate
    for _ in range(steps + 1):
        monthly_pmt = loan_amount * (current_rate / 100.0) / 12.0
        results.append((round(current_rate, 2), monthly_pmt))
        current_rate += 0.10
    return results

def generate_fee_table(loan_amount):
    fees = []
    pt = 0.25
    while pt <= 2.0:
        amt = loan_amount * (pt / 100.0)
        fees.append((round(pt,3), amt))
        pt += 0.125
    return fees

def highlight_rate(rate):
    # e.g. 7.30 => "7.30" => dec_part "30"
    r_str = f"{rate:.2f}"
    if "." in r_str:
        dec_part = r_str.split(".")[1]
        return dec_part in ["30", "70", "90"]
    return False

def highlight_fee_points(points):
    return points in [0.75, 1.0, 1.25, 1.5, 2.0]

def blended_calcs(
    first_loan_amt, first_loan_rate, first_fee_dollars,
    second_loan_amt, second_loan_rate, second_fee_dollars
):
    """Compute total loan, blended rate, total fee, etc."""
    total_loan = first_loan_amt + second_loan_amt

    if total_loan > 0:
        blended_rate = (
            (first_loan_rate * first_loan_amt) +
            (second_loan_rate * second_loan_amt)
        ) / total_loan
    else:
        blended_rate = 0.0

    total_fee_dollars = first_fee_dollars + second_fee_dollars

    if total_loan > 0:
        blended_fee_points = (total_fee_dollars / total_loan) * 100
    else:
        blended_fee_points = 0.0

    second_loan_pmt = second_loan_amt * (second_loan_rate/100.0) / 12.0

    return {
        "total_loan": total_loan,
        "blended_rate": blended_rate,
        "blended_fee_points": blended_fee_points,
        "second_loan_pmt": second_loan_pmt,
        "total_fee_dollars": total_fee_dollars,
    }

# ================================
# Auto-sync logic for 2nd loan
# ================================
def update_2nd_fee_dollars():
    """User changed fee points => recalc fee dollars."""
    st.session_state["last_2nd_fee_method"] = "points"
    amt = st.session_state["second_loan_amount"]
    pts = st.session_state["second_loan_fee_points"]
    st.session_state["second_loan_fee_dollars"] = round(amt * pts / 100.0, 2)

def update_2nd_fee_points():
    """User changed fee dollars => recalc fee points."""
    st.session_state["last_2nd_fee_method"] = "dollars"
    amt = st.session_state["second_loan_amount"]
    dol = st.session_state["second_loan_fee_dollars"]
    if amt != 0:
        st.session_state["second_loan_fee_points"] = round((dol / amt) * 100.0, 3)
    else:
        st.session_state["second_loan_fee_points"] = 0.0

def update_2nd_loan_amount():
    """
    When the user changes '2nd Loan Amount',
    recalc the other fee field from whichever was last changed (points or dollars).
    """
    if st.session_state["last_2nd_fee_method"] == "points":
        update_2nd_fee_dollars()
    else:
        update_2nd_fee_points()

def main():
    st.title("LOI Checker 8000 Pro (Humperdink Edition)")

    # 1) 1st Loan
    st.header("1st Loan Inputs")
    loan_amount = st.number_input("1st Loan Amount", value=200000.0, step=1000.0)
    start_rate  = st.number_input("Starting Interest Rate (%)", value=8.90, step=0.10)

    # 2) Typical Rates
    st.subheader("Typical Rates (Ends in .3, .7, .9)")
    inc_rates = calculate_incremental_rates(loan_amount, start_rate, steps=10)

    featured_rates, additional_rates = [], []
    for (r, monthly) in inc_rates:
        if highlight_rate(r):
            featured_rates.append((r, monthly))
        else:
            additional_rates.append((r, monthly))

    # Display in DataFrame without row numbers
    feat_df = pd.DataFrame(
        [{"Interest Rate": f"{r:.2f}%", "Monthly Payment": f"${m:,.2f}"}
         for (r,m) in featured_rates]
    )
    feat_df.reset_index(drop=True, inplace=True)
    feat_df.index = [""] * len(feat_df)
    st.table(feat_df)

    with st.expander("Show Additional Rates"):
        add_df = pd.DataFrame(
            [{"Interest Rate": f"{r:.2f}%", "Monthly Payment": f"${m:,.2f}"}
             for (r,m) in additional_rates]
        )
        add_df.reset_index(drop=True, inplace=True)
        add_df.index = [""] * len(add_df)
        st.table(add_df)

    # 3) Typical Fees
    st.subheader("Typical Fees")
    fees_list = generate_fee_table(loan_amount)

    featured_fees, additional_fees = [], []
    for (pts, amt) in fees_list:
        if highlight_fee_points(pts):
            featured_fees.append((pts, amt))
        else:
            additional_fees.append((pts, amt))

    st.write("**Featured Fees (0.75, 1.0, 1.25, 1.5, 2.0)**")
    feat_fees_df = pd.DataFrame(
        [{"Points": f"{p} pts", "Fee ($)": f"${a:,.2f}"}
         for (p,a) in featured_fees]
    )
    feat_fees_df.reset_index(drop=True, inplace=True)
    feat_fees_df.index = [""] * len(feat_fees_df)
    st.table(feat_fees_df)

    with st.expander("Show Additional Fees"):
        add_fees_df = pd.DataFrame(
            [{"Points": f"{p} pts", "Fee ($)": f"${a:,.2f}"}
             for (p,a) in additional_fees]
        )
        add_fees_df.reset_index(drop=True, inplace=True)
        add_fees_df.index = [""] * len(add_fees_df)
        st.table(add_fees_df)

    # 4) 2nd Loan & Blended Rate
    with st.expander("2nd Loan & Blended Rate Calculation"):
        st.write("### 1st Loan Rate & Fee")
        first_loan_rate = st.number_input("1st Loan Rate (%)", value=12.25, step=0.25)
        first_loan_fee_dol = st.number_input("1st Loan Fee ($)", value=4000.0, step=1000.0)

        st.write("### 2nd Loan Inputs")

        # Initialize session state
        if "last_2nd_fee_method" not in st.session_state:
            st.session_state["last_2nd_fee_method"] = "points"
        if "second_loan_amount" not in st.session_state:
            st.session_state["second_loan_amount"] = 25000.0
        if "second_loan_fee_points" not in st.session_state:
            st.session_state["second_loan_fee_points"] = 2.0
        if "second_loan_fee_dollars" not in st.session_state:
            st.session_state["second_loan_fee_dollars"] = 500.0

        st.number_input(
            "2nd Loan Amount",
            key="second_loan_amount",
            step=1000.0,
            on_change=update_2nd_loan_amount
        )

        second_loan_rate = st.number_input("2nd Loan Rate (%)", value=9.0, step=0.25)

        colA, colB = st.columns(2)
        with colA:
            st.number_input(
                "2nd Loan Fee (Points)",
                key="second_loan_fee_points",
                step=0.25,
                on_change=update_2nd_fee_dollars
            )
        with colB:
            st.number_input(
                "2nd Loan Fee ($)",
                key="second_loan_fee_dollars",
                step=100.0,
                on_change=update_2nd_fee_points
            )

        # Final calculations
        bc = blended_calcs(
            first_loan_amt=loan_amount,
            first_loan_rate=first_loan_rate,
            first_fee_dollars=first_loan_fee_dol,
            second_loan_amt=st.session_state["second_loan_amount"],
            second_loan_rate=second_loan_rate,
            second_fee_dollars=st.session_state["second_loan_fee_dollars"]
        )

        # Show the total fee (1st + 2nd), plus other results
        st.write("")
        st.markdown("---")
        st.write(f"**Total Fee (1st and 2nd):**  ${bc['total_fee_dollars']:,.2f}")
        st.write(f"**Total Loan Amount:**  ${bc['total_loan']:,.2f}")
        st.write(f"**Blended Interest Rate:**  {bc['blended_rate']:.4f}%")
        st.write(f"**Blended Fee (Points):**  {bc['blended_fee_points']:.4f} pts")
        st.write(f"**2nd Loan Interest-Only Payment:**  ${bc['second_loan_pmt']:,.2f}")

if __name__ == "__main__":
    main()
