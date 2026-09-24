import streamlit as st

from database.supabase_client import get_supabase_client


st.set_page_config(
    page_title="Leather Catalogue",
    page_icon="👜",
    layout="wide",
)


def main():

    st.title("Leather Catalogue")

    st.write(
        "Customer-facing leather catalogue."
    )

    try:
        supabase = get_supabase_client()

        response = (
            supabase
            .table("leather_products")
            .select("*")
            .eq("is_active", True)
            .limit(10)
            .execute()
        )

        st.success("Supabase connection successful.")

        products = response.data

        if not products:
            st.info(
                "No leather products have been added yet."
            )
            return

        st.subheader("Available Leather")

        for product in products:

            st.write(
                f"**{product.get('article_name', 'Unnamed')}**"
            )

            st.write(
                f"Leather ID: {product.get('leather_id', '-')}"
            )

            st.write(
                f"Color: {product.get('color', '-')}"
            )

            st.write(
                f"Thickness: {product.get('thickness', '-')}"
            )

            st.write(
                f"Tannage: {product.get('tannage', '-')}"
            )

            st.divider()

    except Exception as e:

        st.error(
            "Unable to connect to the catalogue database."
        )

        st.exception(e)


if __name__ == "__main__":
    main()
