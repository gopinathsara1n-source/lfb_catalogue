import streamlit as st
from supabase import create_client
from urllib.parse import quote
from io import BytesIO
from urllib.request import urlopen

from PIL import Image, ImageOps


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Leather Catalogue",
    page_icon="👜",
    layout="wide",
)


# =========================================================
# SUPABASE CONNECTION
# =========================================================

@st.cache_resource
def get_supabase():

    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"],
    )


supabase = get_supabase()


# =========================================================
# STORAGE
# =========================================================

BUCKET_NAME = "leather-images"


def get_image_url(filename):

    if not filename:
        return None

    filename = str(filename).strip()

    if not filename:
        return None

    return (
        f"{st.secrets['SUPABASE_URL']}"
        f"/storage/v1/object/public/"
        f"{BUCKET_NAME}/"
        f"{quote(filename)}"
    )


# =========================================================
# LOAD PRODUCTS
# =========================================================

@st.cache_data(ttl=300)
def load_products():

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

    return response.data or []


try:

    products = load_products()

except Exception as e:

    st.error("Unable to load the leather catalogue.")
    st.exception(e)
    st.stop()


# =========================================================
# IMAGE SETTINGS
# =========================================================

# Every catalogue image will be displayed in this ratio.
#
# 16:9 gives the clean horizontal product-card appearance
# similar to the catalogue design you showed.
#
# The image is FITTED, not cropped.
# Therefore the complete leather hide remains visible.

IMAGE_SIZE = (1200, 675)


# =========================================================
# DOWNLOAD + NORMALIZE IMAGE
# =========================================================

@st.cache_data(
    ttl=3600,
    show_spinner=False,
)
def prepare_catalogue_image(image_url):

    if not image_url:
        return None

    try:

        with urlopen(
            image_url,
            timeout=20,
        ) as response:

            image_bytes = response.read()

        image = Image.open(
            BytesIO(image_bytes)
        ).convert("RGB")

        # -------------------------------------------------
        # FIT IMAGE INTO FIXED 16:9 CANVAS
        #
        # ImageOps.contain:
        # - preserves original aspect ratio
        # - does NOT crop the leather
        # - scales large images down
        # -------------------------------------------------

        fitted_image = ImageOps.contain(
            image,
            IMAGE_SIZE,
        )

        # -------------------------------------------------
        # CREATE SAME-SIZE CANVAS FOR EVERY IMAGE
        # -------------------------------------------------

        canvas = Image.new(
            "RGB",
            IMAGE_SIZE,
            "white",
        )

        # -------------------------------------------------
        # CENTER IMAGE
        # -------------------------------------------------

        x = (
            IMAGE_SIZE[0]
            - fitted_image.width
        ) // 2

        y = (
            IMAGE_SIZE[1]
            - fitted_image.height
        ) // 2

        canvas.paste(
            fitted_image,
            (x, y),
        )

        return canvas

    except Exception:
        return None


# =========================================================
# HEADER
# =========================================================

st.title("Leather Catalogue")

st.caption(
    "Explore our leather collection by article, colour, animal, "
    "tannage and origin."
)


# =========================================================
# SEARCH
# =========================================================

search_col, refresh_col = st.columns(
    [12, 1],
    vertical_alignment="center",
)


with search_col:

    search_text = st.text_input(
        "Search",
        placeholder=(
            "Search leather ID, article, colour, animal, "
            "tannage or origin..."
        ),
        label_visibility="collapsed",
    )


with refresh_col:

    if st.button(
        "↻",
        width="stretch",
        help="Refresh catalogue",
    ):

        st.cache_data.clear()
        st.rerun()


st.divider()


# =========================================================
# FILTER VALUES
# =========================================================

animals = sorted(
    {
        str(p["animal"]).strip()
        for p in products
        if p.get("animal")
    }
)


tannages = sorted(
    {
        str(p["tannage"]).strip()
        for p in products
        if p.get("tannage")
    }
)


colors = sorted(
    {
        str(p["color"]).strip()
        for p in products
        if p.get("color")
    }
)


origins = sorted(
    {
        str(p["origin"]).strip()
        for p in products
        if p.get("origin")
    }
)


# =========================================================
# MAIN LAYOUT
# =========================================================

filter_col, catalogue_col = st.columns(
    [1.2, 5],
    gap="large",
)


# =========================================================
# FILTER PANEL
# =========================================================

with filter_col:

    with st.container(border=True):

        st.subheader("Filter")

        st.caption(
            "Narrow down the leather collection."
        )

        selected_animals = st.multiselect(
            "Animal",
            options=animals,
            placeholder="All animals",
        )

        selected_tannages = st.multiselect(
            "Tannage",
            options=tannages,
            placeholder="All tannages",
        )

        selected_colors = st.multiselect(
            "Colour",
            options=colors,
            placeholder="All colours",
        )

        selected_origins = st.multiselect(
            "Origin",
            options=origins,
            placeholder="All origins",
        )

        st.divider()

        st.caption(
            f"{len(products)} total leather articles"
        )


# =========================================================
# FILTER PRODUCTS
# =========================================================

filtered_products = []

search_lower = (
    search_text
    .strip()
    .lower()
)


for product in products:

    # -----------------------------------------------------
    # SEARCH
    # -----------------------------------------------------

    searchable_text = " ".join(
        [
            str(product.get("leather_id") or ""),
            str(product.get("article_name") or ""),
            str(product.get("color") or ""),
            str(product.get("thickness") or ""),
            str(product.get("tannage") or ""),
            str(product.get("animal") or ""),
            str(product.get("origin") or ""),
        ]
    ).lower()


    if (
        search_lower
        and search_lower not in searchable_text
    ):

        continue


    # -----------------------------------------------------
    # ANIMAL
    # -----------------------------------------------------

    if selected_animals:

        if product.get("animal") not in selected_animals:

            continue


    # -----------------------------------------------------
    # TANNAGE
    # -----------------------------------------------------

    if selected_tannages:

        if product.get("tannage") not in selected_tannages:

            continue


    # -----------------------------------------------------
    # COLOR
    # -----------------------------------------------------

    if selected_colors:

        if product.get("color") not in selected_colors:

            continue


    # -----------------------------------------------------
    # ORIGIN
    # -----------------------------------------------------

    if selected_origins:

        if product.get("origin") not in selected_origins:

            continue


    filtered_products.append(product)


# =========================================================
# CATALOGUE HEADER
# =========================================================

with catalogue_col:

    result_col, sort_col = st.columns(
        [4, 1],
        vertical_alignment="center",
    )


    with result_col:

        st.subheader(
            "Available Leather"
        )

        st.caption(
            f"Showing {len(filtered_products)} of "
            f"{len(products)} leather articles"
        )


    with sort_col:

        sort_option = st.selectbox(
            "Sort",
            [
                "Leather ID",
                "Article",
                "Animal",
                "Colour",
            ],
            label_visibility="collapsed",
        )


# =========================================================
# SORT
# =========================================================

if sort_option == "Leather ID":

    filtered_products.sort(
        key=lambda x: str(
            x.get("leather_id") or ""
        )
    )


elif sort_option == "Article":

    filtered_products.sort(
        key=lambda x: str(
            x.get("article_name") or ""
        ).lower()
    )


elif sort_option == "Animal":

    filtered_products.sort(
        key=lambda x: str(
            x.get("animal") or ""
        ).lower()
    )


elif sort_option == "Colour":

    filtered_products.sort(
        key=lambda x: str(
            x.get("color") or ""
        ).lower()
    )


# =========================================================
# EMPTY RESULT
# =========================================================

if not filtered_products:

    with catalogue_col:

        with st.container(border=True):

            st.info(
                "No leather articles match your search or filters."
            )

            st.write(
                "Try clearing one or more filters."
            )

    st.stop()


# =========================================================
# PRODUCT GRID
# =========================================================

with catalogue_col:

    # Four products per row.
    #
    # Streamlit columns adapt automatically to
    # different screen sizes.

    for row_start in range(
        0,
        len(filtered_products),
        4,
    ):

        row_products = filtered_products[
            row_start:row_start + 4
        ]


        columns = st.columns(
            4,
            gap="medium",
        )


        for column, product in zip(
            columns,
            row_products,
        ):

            with column:

                # =================================================
                # PRODUCT CARD
                # =================================================

                with st.container(
                    border=True
                ):

                    leather_id = str(
                        product.get(
                            "leather_id"
                        ) or ""
                    )


                    # =================================================
                    # IMAGE URLS
                    # =================================================

                    main_image_url = get_image_url(
                        product.get(
                            "main_photo"
                        )
                    )


                    closeup_image_url = get_image_url(
                        product.get(
                            "closeup_photo"
                        )
                    )


                    # =================================================
                    # PREPARE IMAGES
                    # =================================================

                    main_image = (
                        prepare_catalogue_image(
                            main_image_url
                        )
                        if main_image_url
                        else None
                    )


                    closeup_image = (
                        prepare_catalogue_image(
                            closeup_image_url
                        )
                        if closeup_image_url
                        else None
                    )


                    # =================================================
                    # MAIN / CLOSE-UP SELECTOR
                    # =================================================

                    image_options = []

                    if main_image is not None:

                        image_options.append(
                            "Main"
                        )

                    if closeup_image is not None:

                        image_options.append(
                            "Close-up"
                        )


                    # If neither image exists
                    if not image_options:

                        st.info(
                            "Image unavailable"
                        )

                        selected_image = None
                        selected_image_name = None


                    else:

                        # -------------------------------------------------
                        # TWO IMAGE SLIDES
                        # -------------------------------------------------

                        if len(image_options) == 2:

                            selected_image_name = (
                                st.segmented_control(
                                    "Photo",
                                    image_options,
                                    default="Main",
                                    label_visibility="collapsed",
                                    width="stretch",
                                    key=f"photo_{leather_id}",
                                )
                            )

                        else:

                            selected_image_name = (
                                image_options[0]
                            )


                        # -------------------------------------------------
                        # SELECT IMAGE
                        # -------------------------------------------------

                        if (
                            selected_image_name
                            == "Close-up"
                        ):

                            selected_image = (
                                closeup_image
                            )

                        else:

                            selected_image = (
                                main_image
                            )


                        # -------------------------------------------------
                        # DISPLAY IMAGE
                        # -------------------------------------------------

                        if selected_image is not None:

                            st.image(
                                selected_image,
                                width="stretch",
                            )


                            # -------------------------------------------------
                            # IMAGE ACTIONS
                            # -------------------------------------------------

                            zoom_col, photo_col = st.columns(
                                [1, 1],
                                gap="small",
                            )


                            with zoom_col:

                                with st.popover(
                                    "🔍 Check photo",
                                    width="stretch",
                                ):

                                    st.caption(
                                        selected_image_name
                                    )

                                    st.image(
                                        selected_image,
                                        width="stretch",
                                    )


                            with photo_col:

                                if len(image_options) == 2:

                                    st.caption(
                                        f"{image_options.index(selected_image_name) + 1}"
                                        f"/{len(image_options)}"
                                    )


                    # =================================================
                    # ARTICLE
                    # =================================================

                    st.markdown(
                        f"**{product.get('article_name', '-') }**"
                    )


                    # =================================================
                    # LEATHER ID
                    # =================================================

                    st.caption(
                        f"Leather ID: "
                        f"{product.get('leather_id', '-')}"
                    )


                    # =================================================
                    # BASIC DETAILS
                    # =================================================

                    st.write(
                        f"**Colour:** "
                        f"{product.get('color', '-')}"
                    )


                    st.write(
                        f"**Thickness:** "
                        f"{product.get('thickness', '-')}"
                    )


                    # =================================================
                    # MORE DETAILS
                    # =================================================

                    with st.expander(
                        "View details"
                    ):

                        st.write(
                            f"**Animal:** "
                            f"{product.get('animal', '-')}"
                        )

                        st.write(
                            f"**Tannage:** "
                            f"{product.get('tannage', '-')}"
                        )

                        st.write(
                            f"**Origin:** "
                            f"{product.get('origin', '-')}"
                        )


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "Bhartiya Fashions • Leather Catalogue"
)
