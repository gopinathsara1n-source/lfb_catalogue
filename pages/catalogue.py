import streamlit as st

from database.supabase_client import get_supabase_client
from components.product_card import display_product


st.title("Leather Catalogue")


try:

    supabase = get_supabase_client()

    response = (
        supabase
        .table("leather_products")
        .select("*")
        .eq("is_active", True)
        .execute()
    )

    products = response.data

    if not products:

        st.info(
            "No leather products are currently available."
        )

    else:

        for product in products:

            display_product(product)

            st.divider()


except Exception as e:

    st.error(
        "Unable to load the leather catalogue."
    )

    st.exception(e)
