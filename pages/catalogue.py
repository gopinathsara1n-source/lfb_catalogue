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

# Fixed catalogue-card ratio.
#
# Every product card gets exactly the same visual
# image area regardless of the original photo shape.

CARD_SIZE = (1200, 675)


# Larger inspection viewport inside detail dialog.

DETAIL_VIEWPORT = (1200, 800)


# =========================================================
# DOWNLOAD ORIGINAL IMAGE
# =========================================================

@st.cache_data(
    ttl=3600,
    show_spinner=False,
)
def load_image(image_url):

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

        return image

    except Exception:

        return None


# =========================================================
# CREATE UNIFORM CARD IMAGE
# =========================================================

def make_card_image(image):

    if image is None:
        return None

    # Preserve entire leather image.
    fitted = ImageOps.contain(
        image,
        CARD_SIZE,
    )

    # White background.
    canvas = Image.new(
        "RGB",
        CARD_SIZE,
        "white",
    )

    # Center image.
    x = (
        CARD_SIZE[0]
        - fitted.width
    ) // 2

    y = (
        CARD_SIZE[1]
        - fitted.height
    ) // 2

    canvas.paste(
        fitted,
        (x, y),
    )

    return canvas


# =========================================================
# CREATE ZOOMED IMAGE
# =========================================================

def make_zoom_view(
    image,
    zoom_percent,
    horizontal_position,
    vertical_position,
):

    if image is None:
        return None

    viewport_width = DETAIL_VIEWPORT[0]
    viewport_height = DETAIL_VIEWPORT[1]

    original_width = image.width
    original_height = image.height

    # -----------------------------------------------------
    # BASE SCALE
    #
    # At 100%, the complete image fits inside the
    # inspection viewport.
    # -----------------------------------------------------

    base_scale = min(
        viewport_width / original_width,
        viewport_height / original_height,
    )

    scale = (
        base_scale
        * zoom_percent
        / 100
    )

    new_width = max(
        1,
        int(original_width * scale),
    )

    new_height = max(
        1,
        int(original_height * scale),
    )

    # -----------------------------------------------------
    # RESIZE
    # -----------------------------------------------------

    resized = image.resize(
        (
            new_width,
            new_height,
        ),
        Image.Resampling.LANCZOS,
    )

    # -----------------------------------------------------
    # IF IMAGE IS SMALLER THAN VIEWPORT
    # -----------------------------------------------------

    if (
        resized.width <= viewport_width
        and resized.height <= viewport_height
    ):

        canvas = Image.new(
            "RGB",
            (
                viewport_width,
                viewport_height,
            ),
            "white",
        )

        x = (
            viewport_width
            - resized.width
        ) // 2

        y = (
            viewport_height
            - resized.height
        ) // 2

        canvas.paste(
            resized,
            (x, y),
        )

        return canvas

    # -----------------------------------------------------
    # CALCULATE MAX PAN
    # -----------------------------------------------------

    max_left = max(
        0,
        resized.width
        - viewport_width,
    )

    max_top = max(
        0,
        resized.height
        - viewport_height,
    )

    # -----------------------------------------------------
    # HORIZONTAL POSITION
    #
    # 0   = far left
    # 50  = center
    # 100 = far right
    # -----------------------------------------------------

    left = int(
        max_left
        * horizontal_position
        / 100
    )

    # -----------------------------------------------------
    # VERTICAL POSITION
    #
    # 0   = top
    # 50  = center
    # 100 = bottom
    # -----------------------------------------------------

    top = int(
        max_top
        * vertical_position
        / 100
    )

    # -----------------------------------------------------
    # CROP VIEWPORT
    # -----------------------------------------------------

    right = left + viewport_width

    bottom = top + viewport_height

    cropped = resized.crop(
        (
            left,
            top,
            right,
            bottom,
        )
    )

    return cropped


# =========================================================
# DETAIL DIALOG
# =========================================================

@st.dialog(
    "Leather Details",
    width="large",
    dismissible=True,
)
def show_product_details(product):

    leather_id = str(
        product.get("leather_id")
        or "-"
    )

    article_name = str(
        product.get("article_name")
        or "-"
    )

    main_url = get_image_url(
        product.get("main_photo")
    )

    closeup_url = get_image_url(
        product.get("closeup_photo")
    )

    # -----------------------------------------------------
    # LOAD ORIGINAL IMAGES
    # -----------------------------------------------------

    main_image = (
        load_image(main_url)
        if main_url
        else None
    )

    closeup_image = (
        load_image(closeup_url)
        if closeup_url
        else None
    )

    # -----------------------------------------------------
    # AVAILABLE PHOTOS
    # -----------------------------------------------------

    photo_options = []

    if main_image is not None:
        photo_options.append("Main")

    if closeup_image is not None:
        photo_options.append("Close-up")

    # -----------------------------------------------------
    # PHOTO SELECTION
    # -----------------------------------------------------

    if len(photo_options) == 2:

        selected_photo = st.segmented_control(
            "Photo",
            photo_options,
            default="Main",
            width="stretch",
            key=f"detail_photo_{leather_id}",
        )

    elif len(photo_options) == 1:

        selected_photo = photo_options[0]

    else:

        selected_photo = None


    # -----------------------------------------------------
    # SELECT IMAGE
    # -----------------------------------------------------

    if selected_photo == "Close-up":

        selected_image = closeup_image

    else:

        selected_image = main_image


    # =====================================================
    # MAIN DETAIL LAYOUT
    # =====================================================

    photo_col, details_col = st.columns(
        [1.55, 1],
        gap="large",
    )


    # =====================================================
    # LEFT SIDE — LARGE PHOTO
    # =====================================================

    with photo_col:

        st.markdown(
            f"### {article_name}"
        )

        if selected_image is None:

            st.info(
                "No image available."
            )

        else:

            # -------------------------------------------------
            # ZOOM CONTROL
            # -------------------------------------------------

            zoom_col, reset_col = st.columns(
                [4, 1],
                vertical_alignment="bottom",
            )


            with zoom_col:

                zoom_percent = st.slider(
                    "Zoom",
                    min_value=50,
                    max_value=400,
                    value=100,
                    step=10,
                    format="%d%%",
                    key=f"zoom_{leather_id}",
                )


            with reset_col:

                reset_zoom = st.button(
                    "Reset",
                    key=f"reset_zoom_{leather_id}",
                    width="stretch",
                )


            if reset_zoom:

                st.session_state[
                    f"zoom_{leather_id}"
                ] = 100

                st.session_state[
                    f"xpos_{leather_id}"
                ] = 50

                st.session_state[
                    f"ypos_{leather_id}"
                ] = 50

                st.rerun()


            # -------------------------------------------------
            # POSITION CONTROLS
            #
            # These become useful when zoomed in.
            # -------------------------------------------------

            position_col1, position_col2 = st.columns(
                2,
                gap="medium",
            )


            with position_col1:

                horizontal_position = st.slider(
                    "Horizontal",
                    min_value=0,
                    max_value=100,
                    value=50,
                    step=5,
                    help=(
                        "Move the zoomed image "
                        "left or right."
                    ),
                    key=f"xpos_{leather_id}",
                )


            with position_col2:

                vertical_position = st.slider(
                    "Vertical",
                    min_value=0,
                    max_value=100,
                    value=50,
                    step=5,
                    help=(
                        "Move the zoomed image "
                        "up or down."
                    ),
                    key=f"ypos_{leather_id}",
                )


            # -------------------------------------------------
            # CREATE ZOOM VIEW
            # -------------------------------------------------

            displayed_image = make_zoom_view(
                selected_image,
                zoom_percent,
                horizontal_position,
                vertical_position,
            )


            # -------------------------------------------------
            # DISPLAY
            # -------------------------------------------------

            st.image(
                displayed_image,
                width="stretch",
            )


            # -------------------------------------------------
            # IMAGE INFORMATION
            # -------------------------------------------------

            st.caption(
                f"{selected_photo} • "
                f"Zoom {zoom_percent}%"
            )


    # =====================================================
    # RIGHT SIDE — DETAILS
    # =====================================================

    with details_col:

        st.markdown(
            "### Product Information"
        )

        st.divider()


        # -------------------------------------------------
        # LEATHER ID
        # -------------------------------------------------

        st.markdown(
            f"**Leather ID**  \n"
            f"{leather_id}"
        )

        st.divider()


        # -------------------------------------------------
        # ARTICLE
        # -------------------------------------------------

        st.markdown(
            f"**Article Name**  \n"
            f"{product.get('article_name') or '-'}"
        )

        st.divider()


        # -------------------------------------------------
        # COLOUR
        # -------------------------------------------------

        st.markdown(
            f"**Colour**  \n"
            f"{product.get('color') or '-'}"
        )

        st.divider()


        # -------------------------------------------------
        # THICKNESS
        # -------------------------------------------------

        st.markdown(
            f"**Thickness**  \n"
            f"{product.get('thickness') or '-'}"
        )

        st.divider()


        # -------------------------------------------------
        # ANIMAL
        # -------------------------------------------------

        st.markdown(
            f"**Animal**  \n"
            f"{product.get('animal') or '-'}"
        )

        st.divider()


        # -------------------------------------------------
        # TANNAGE
        # -------------------------------------------------

        st.markdown(
            f"**Tannage**  \n"
            f"{product.get('tannage') or '-'}"
        )

        st.divider()


        # -------------------------------------------------
        # ORIGIN
        # -------------------------------------------------

        st.markdown(
            f"**Origin**  \n"
            f"{product.get('origin') or '-'}"
        )

        st.divider()


        # -------------------------------------------------
        # PHOTO STATUS
        # -------------------------------------------------

        if main_image is not None:

            st.success(
                "Main photo available"
            )

        else:

            st.warning(
                "Main photo unavailable"
            )


        if closeup_image is not None:

            st.success(
                "Close-up photo available"
            )

        else:

            st.warning(
                "Close-up photo unavailable"
            )


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


    if selected_animals:

        if (
            product.get("animal")
            not in selected_animals
        ):

            continue


    if selected_tannages:

        if (
            product.get("tannage")
            not in selected_tannages
        ):

            continue


    if selected_colors:

        if (
            product.get("color")
            not in selected_colors
        ):

            continue


    if selected_origins:

        if (
            product.get("origin")
            not in selected_origins
        ):

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

        with st.container(
            border=True
        ):

            st.info(
                "No leather articles match "
                "your search or filters."
            )

            st.write(
                "Try clearing one or more filters."
            )

    st.stop()


# =========================================================
# PRODUCT GRID
# =========================================================

with catalogue_col:

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

                with st.container(
                    border=True
                ):

                    # =================================================
                    # PRODUCT IMAGE
                    # =================================================

                    main_url = get_image_url(
                        product.get(
                            "main_photo"
                        )
                    )


                    main_original = (
                        load_image(main_url)
                        if main_url
                        else None
                    )


                    card_image = (
                        make_card_image(
                            main_original
                        )
                        if main_original
                        else None
                    )


                    if card_image is not None:

                        st.image(
                            card_image,
                            width="stretch",
                        )

                    else:

                        st.info(
                            "Image unavailable"
                        )


                    # =================================================
                    # ARTICLE NAME
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
                    # VIEW DETAILS
                    # =================================================

                    if st.button(
                        "View details",
                        key=(
                            f"details_"
                            f"{product.get('leather_id')}"
                        ),
                        width="stretch",
                        icon=":material/zoom_in:",
                    ):

                        show_product_details(
                            product
                        )


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "Bhartiya Fashions • Leather Catalogue"
)
