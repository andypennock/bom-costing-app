
import streamlit as st
import pandas as pd

# Page config
st.set_page_config(page_title="BOM Costing Tool", layout="centered")
st.title("📊 BOM Costing Tool")

# Upload section
st.sidebar.header("Upload Files")
bom_file = st.sidebar.file_uploader("Upload BOM CSV", type="csv")
purchase_file = st.sidebar.file_uploader("Upload Purchase Cost CSV", type="csv")
labour_rate = st.sidebar.number_input("Enter Labour Rate (£/hr)", value=28.0, step=0.01)

# Initialize dataframes
bom_df = None
purchase_df = None

if bom_file and purchase_file:
    bom_df = pd.read_csv(bom_file)
    purchase_df = pd.read_csv(purchase_file)

    # Convert to consistent types
    bom_df["BOM Variant"] = bom_df["BOM Variant"].astype(str)
    bom_df["Component Variant"] = bom_df["Component Variant"].astype(str)
    purchase_df["Variant code"] = purchase_df["Variant code"].astype(str)

    # Component cost lookup
    cost_lookup = dict(zip(purchase_df["Variant code"], purchase_df["Estimated cost"]))
    desc_lookup = dict(zip(purchase_df["Variant code"], purchase_df["Variant description"]))

    st.success("Files loaded. Select a BOM Variant to calculate costs.")
    bom_variants = bom_df["BOM Variant"].unique().tolist()
    selected_bom = st.selectbox("Select BOM Variant", sorted(bom_variants), key="bom_search")


    # Recursive calculation function
    def calculate_cost(variant_code, qty=1, level=0, parent="ROOT"):
        rows = []
        sub_bom = bom_df[bom_df["BOM Variant"] == variant_code]
        total_cost = 0

        if not sub_bom.empty:
            time = sub_bom["Time (hrs)"].max()
            labour_cost = (time * labour_rate * qty) if pd.notnull(time) else 0
            rows.append([level, parent, variant_code, "Assembly Labour", qty, "Labour", 0, labour_cost, labour_cost])
            total_cost += labour_cost

        for _, row in sub_bom.iterrows():
            comp = row["Component Variant"]
            q = row["Quantity"]
            build_per = row["Build per"]
            adj_qty = qty * q / build_per

            if comp in cost_lookup:
                unit_cost = cost_lookup[comp]
                desc = desc_lookup.get(comp, "N/A")
                cost = adj_qty * unit_cost
                rows.append([level, variant_code, comp, desc, adj_qty, "Purchased", unit_cost, 0, cost])
                total_cost += cost
            else:
                sub_cost, sub_rows = calculate_cost(comp, adj_qty, level + 1, variant_code)
                unit_cost = sub_cost / adj_qty if adj_qty else 0
                rows.extend(sub_rows)
                rows.append([level, variant_code, comp, "Manufactured", adj_qty, "Manufactured", unit_cost, 0, sub_cost])
                total_cost += sub_cost

        return total_cost, rows

    if st.button("Calculate Cost"):
        total, rows = calculate_cost(selected_bom)
        result_df = pd.DataFrame(rows, columns=[
            "Level", "Parent", "Component", "Description", "Quantity", "Type",
            "Unit Cost (£)", "Labour Cost (£)", "Total Cost (£)"
        ])

        st.subheader(f"Total Cost to Manufacture {selected_bom}: £{total:.2f}")
        st.dataframe(result_df, use_container_width=True)

        csv = result_df.to_csv(index=False).encode("utf-8")
        st.download_button("Download Breakdown as CSV", csv, f"{selected_bom}_cost_breakdown.csv", "text/csv")

else:
    st.info("Please upload both BOM and Purchase CSV files to begin.")
