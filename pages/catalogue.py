import streamlit as st
from supabase import create_client
from urllib.parse import quote


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Leather Catalogue",
    page_icon="👜",
    layout="wide"
)


# =========================================================
# SUPABASE CONNECTION
# =========================================================

supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)


# =========================================================
# STORAGE CONFIGURATION
# =========================================================

BUCKET_NAME = "leather-images"


def get_image_url(filename):
    """
    Convert a Supabase Storage filename into a public image URL.
    Handles filenames containing spaces and special characters.
    """

    if not filename:
        return None

    filename = str(filename).strip()

    if not filename:
        return None

    encoded_filename = quote(filename)

    return (
        f"{st.secrets['SUPABASE_URL']}"
        f"/storage/v1/object/public/"
        f"{BUCKET_NAME}/"
        f"{encoded_filename}"
    )


# =========================================================
# LOAD PRODUCTS
# =========================================================

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


# =========================================================
# PAGE HEADER
# =========================================================

st.title("Leather Catalogue")

st.caption("Customer-facing leather catalogue.")


# =========================================================
# EMPTY STATE
# =========================================================

if not products:

    st.info("No leather products have been added yet.")
    st.stop()


st.success(f"{len(products)} leather products available")


# =========================================================
# DISPLAY PRODUCTS
# =========================================================

for product in products:

    st.subheader(product["article_name"])

    # -----------------------------------------------------
    # IMAGE URLS
    # -----------------------------------------------------

    main_image_url = get_image_url(
        product.get("main_photo")
    )

    closeup_image_url = get_image_url(
        product.get("closeup_photo")
    )

    # -----------------------------------------------------
    # PRODUCT IMAGES
    # -----------------------------------------------------

    image_col1, image_col2 = st.columns(2)

    with image_col1:

        if main_image_url:

            st.image(
                main_image_url,
                caption="Main View",
                use_container_width=True
            )

        else:

            st.info("Main image not available.")

    with image_col2:

        if closeup_image_url:

            st.image(
                closeup_image_url,
                caption="Close-up",
                use_container_width=True
            )

        else:

            st.info("Close-up image not available.")

    # -----------------------------------------------------
    # PRODUCT DETAILS
    # -----------------------------------------------------

    detail_col1, detail_col2 = st.columns(2)

    with detail_col1:

        st.write(
            f"**Leather ID:** {product.get('leather_id', '-')}"
        )

        st.write(
            f"**Color:** {product.get('color', '-')}"
        )

        st.write(
            f"**Thickness:** {product.get('thickness', '-')}"
        )

        st.write(
            f"**Tannage:** {product.get('tannage', '-')}"
        )

    with detail_col2:

        st.write(
            f"**Animal:** {product.get('animal', '-')}"
        )

        st.write(
            f"**Origin:** {product.get('origin', '-')}"
        )

    st.divider()
