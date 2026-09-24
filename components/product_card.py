import streamlit as st


def display_product(product):

    st.subheader(
        product.get("article_name", "Unnamed Leather")
    )

    st.write(
        f"**Leather ID:** "
        f"{product.get('leather_id', '-')}"
    )

    st.write(
        f"**Color:** "
        f"{product.get('color', '-')}"
    )

    st.write(
        f"**Thickness:** "
        f"{product.get('thickness', '-')}"
    )

    st.write(
        f"**Tannage:** "
        f"{product.get('tannage', '-')}"
    )

    st.write(
        f"**Animal:** "
        f"{product.get('animal', '-')}"
    )

    st.write(
        f"**Origin:** "
        f"{product.get('origin', '-')}"
    )
