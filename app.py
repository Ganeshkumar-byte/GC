import streamlit as st
import pandas as pd

st.set_page_config(page_title="GC Retention Finder", layout="centered")

st.title("GC Retention Time Finder")

# Upload Excel file
uploaded_file = st.file_uploader("Upload GC Database (Excel)", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    # Clean data
    df['Retention Time'] = pd.to_numeric(df['Retention Time'], errors='coerce')
    df.dropna(subset=['Retention Time'], inplace=True)

    # User input
    input_rt = st.number_input("Enter retention time:", min_value=0.0, format="%.4f")

    # Tolerance input (optional control)
    tolerance = st.number_input("Tolerance for exact match:", value=0.001, format="%.6f")

    if st.button("Find Peaks"):

        # Calculate difference
        df['diff'] = (df['Retention Time'] - input_rt).abs()

        # Get closest peaks
        closest_peaks = df.sort_values(by='diff').head(3)
        closest_peaks_display = closest_peaks.rename(columns={
            'Compound Name': 'NAME',
            'Retention Time': 'RETENTION TIME'
        })

        # Check exact match
        exact_match_found = (df['diff'] < tolerance).any()

        if exact_match_found:
            matched_entries = df[df['diff'] < tolerance]
            matched_names = matched_entries['Compound Name'].tolist()

            matched_display = matched_entries.rename(columns={
                'Compound Name': 'NAME',
                'Retention Time': 'RETENTION TIME'
            })

            st.success(
                f"Exact match found for: {', '.join(matched_names)} "
                f"(within {tolerance} tolerance)"
            )

            st.subheader("Exact Match(es)")
            st.dataframe(matched_display[['NAME', 'RETENTION TIME']])

        else:
            st.warning(
                f"No exact match found for {input_rt}. "
                "Elution may vary depending on conditions."
            )

            st.subheader("Nearest 3 Peaks")
            st.dataframe(closest_peaks_display[['NAME', 'RETENTION TIME']])
