import streamlit as st
from supabase import create_client


# ---------------------------------------------------------
# SUPABASE CONNECTION
# ---------------------------------------------------------

supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)


# ---------------------------------------------------------
# LOAD PRODUCTS
# ---------------------------------------------------------

try:
    response = (
        supabase
        .table("leather_products")
        .select(
            """
            leather_id,
            article_name,
            color,
            thickness,
            tannage,
            animal,
            origin,
            main_photo,
            closeup_photo,
            is_active
            """
        )
        .eq("is_active", True)
        .order("leather_id")
        .execute()
    )

    products = response.data or []

except Exception as e:
    st.error("Unable to load the leather catalogue.")
    st.exception(e)
    st.stop()


# ---------------------------------------------------------
# DISPLAY
# ---------------------------------------------------------

st.title("Leather Catalogue")

st.caption("Customer-facing leather catalogue.")

if not products:
    st.info("No leather products have been added yet.")
    st.stop()

st.success(f"{len(products)} leather products available")


for product in products:

    st.subheader(product["article_name"])

    col1, col2 = st.columns(2)

    with col1:
        st.write(f"**Leather ID:** {product['leather_id']}")
        st.write(f"**Color:** {product['color']}")
        st.write(f"**Thickness:** {product['thickness']}")
        st.write(f"**Tannage:** {product['tannage']}")

    with col2:
        st.write(f"**Animal:** {product['animal']}")
        st.write(f"**Origin:** {product['origin']}")

    st.divider()
