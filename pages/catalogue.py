import streamlit as st
from supabase import create_client
from urllib.parse import quote
from io import BytesIO
from urllib.request import urlopen
import base64

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
CARD_SIZE = (1200, 675)


# Interactive viewer height.
VIEWER_HEIGHT = 650


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
# IMAGE -> BASE64
# =========================================================

def image_to_base64(image):

    if image is None:
        return None

    buffer = BytesIO()

    image.save(
        buffer,
        format="JPEG",
        quality=95,
    )

    encoded = base64.b64encode(
        buffer.getvalue()
    ).decode("utf-8")

    return encoded


# =========================================================
# CREATE UNIFORM CARD IMAGE
# =========================================================

def make_card_image(image):

    if image is None:
        return None

    fitted = ImageOps.contain(
        image,
        CARD_SIZE,
    )

    canvas = Image.new(
        "RGB",
        CARD_SIZE,
        "white",
    )

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
# INTERACTIVE IMAGE VIEWER
#
# Features:
#   - Mouse wheel zoom
#   - Click + drag pan
#   - Double click reset
#   - + / - controls
#   - Reset button
#   - Zoom around mouse cursor
# =========================================================

def interactive_image_viewer(
    image,
    height=650,
    key="image_viewer",
):

    if image is None:

        st.info(
            "No image available."
        )

        return

    image_base64 = image_to_base64(image)

    if not image_base64:

        st.info(
            "Unable to display image."
        )

        return

    html = f"""
<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width,
               initial-scale=1.0">

<style>

* {{
    box-sizing: border-box;
}}

html,
body {{

    margin: 0;
    padding: 0;

    width: 100%;
    height: 100%;

    overflow: hidden;

    background: #111;

    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;
}}


/* =====================================================
   VIEWER
   ===================================================== */

.viewer {{

    position: relative;

    width: 100%;

    height: {height}px;

    overflow: hidden;

    background:
        #111;

    border-radius: 10px;

    border:
        1px solid rgba(
            255,
            255,
            255,
            0.12
        );

    user-select: none;

    touch-action: none;

    cursor: grab;
}}


/* =====================================================
   IMAGE
   ===================================================== */

.viewer-image {{

    position: absolute;

    left: 50%;
    top: 50%;

    max-width: none;
    max-height: none;

    width: auto;
    height: auto;

    transform-origin: center center;

    will-change:
        transform;

    pointer-events: none;

    user-select: none;

    -webkit-user-drag: none;

    image-rendering:
        auto;
}}


/* =====================================================
   DRAGGING
   ===================================================== */

.viewer.dragging {{

    cursor: grabbing;
}}


/* =====================================================
   CONTROLS
   ===================================================== */

.controls {{

    position: absolute;

    top: 14px;
    right: 14px;

    display: flex;

    gap: 6px;

    z-index: 20;
}}


.control-button {{

    width: 38px;
    height: 38px;

    border: 0;

    border-radius: 8px;

    background:
        rgba(
            25,
            25,
            25,
            0.82
        );

    color: white;

    font-size: 20px;

    font-weight: 500;

    cursor: pointer;

    display: flex;

    align-items: center;

    justify-content: center;

    backdrop-filter:
        blur(8px);

    box-shadow:
        0 2px 8px
        rgba(
            0,
            0,
            0,
            0.25
        );
}}


.control-button:hover {{

    background:
        rgba(
            55,
            55,
            55,
            0.95
        );
}}


/* =====================================================
   RESET BUTTON
   ===================================================== */

.reset-button {{

    padding:
        0 12px;

    width: auto;

    font-size: 13px;
}}


/* =====================================================
   ZOOM LABEL
   ===================================================== */

.zoom-label {{

    position: absolute;

    left: 14px;
    bottom: 14px;

    padding:
        6px 10px;

    border-radius: 7px;

    background:
        rgba(
            20,
            20,
            20,
            0.78
        );

    color: white;

    font-size: 12px;

    z-index: 20;

    backdrop-filter:
        blur(8px);
}}


/* =====================================================
   HELP TEXT
   ===================================================== */

.help-text {{

    position: absolute;

    left: 50%;

    bottom: 14px;

    transform:
        translateX(-50%);

    padding:
        6px 12px;

    border-radius: 7px;

    background:
        rgba(
            20,
            20,
            20,
            0.70
        );

    color:
        rgba(
            255,
            255,
            255,
            0.85
        );

    font-size: 12px;

    z-index: 20;

    pointer-events: none;

    backdrop-filter:
        blur(8px);
}}


</style>

</head>


<body>


<div
    id="viewer"
    class="viewer"
>


    <!-- =================================================
         CONTROLS
         ================================================= -->

    <div class="controls">

        <button
            id="zoomOut"
            class="control-button"
            title="Zoom out"
        >
            −
        </button>


        <button
            id="zoomIn"
            class="control-button"
            title="Zoom in"
        >
            +
        </button>


        <button
            id="reset"
            class="control-button reset-button"
            title="Reset photo"
        >
            Reset
        </button>

    </div>


    <!-- =================================================
         IMAGE
         ================================================= -->

    <img
        id="image"
        class="viewer-image"
        src="data:image/jpeg;base64,{image_base64}"
        draggable="false"
    />


    <!-- =================================================
         ZOOM LABEL
         ================================================= -->

    <div
        id="zoomLabel"
        class="zoom-label"
    >
        100%
    </div>


    <!-- =================================================
         HELP
         ================================================= -->

    <div
        class="help-text"
    >
        Scroll to zoom • Drag to move • Double-click to reset
    </div>


</div>


<script>


// =======================================================
// ELEMENTS
// =======================================================

const viewer =
    document.getElementById(
        "viewer"
    );


const image =
    document.getElementById(
        "image"
    );


const zoomLabel =
    document.getElementById(
        "zoomLabel"
    );


const zoomIn =
    document.getElementById(
        "zoomIn"
    );


const zoomOut =
    document.getElementById(
        "zoomOut"
    );


const resetButton =
    document.getElementById(
        "reset"
    );


// =======================================================
// STATE
// =======================================================

let scale = 1;

let translateX = 0;

let translateY = 0;


let dragging = false;

let startX = 0;

let startY = 0;

let startTranslateX = 0;

let startTranslateY = 0;


// =======================================================
// LIMITS
// =======================================================

const MIN_SCALE = 0.5;

const MAX_SCALE = 8.0;


// =======================================================
// UPDATE LABEL
// =======================================================

function updateLabel() {{

    zoomLabel.textContent =
        Math.round(
            scale * 100
        ) + "%";
}}


// =======================================================
// APPLY TRANSFORM
// =======================================================

function applyTransform() {{

    image.style.transform =
        "translate(-50%, -50%) " +
        "translate(" +
        translateX +
        "px, " +
        translateY +
        "px) " +
        "scale(" +
        scale +
        ")";

    updateLabel();
}}


// =======================================================
// RESET
// =======================================================

function resetViewer() {{

    scale = 1;

    translateX = 0;

    translateY = 0;

    applyTransform();
}}


// =======================================================
// ZOOM
// =======================================================

function zoomAt(
    newScale,
    mouseX,
    mouseY
) {{

    newScale =
        Math.max(
            MIN_SCALE,
            Math.min(
                MAX_SCALE,
                newScale
            )
        );


    if (
        Math.abs(
            newScale - scale
        ) < 0.0001
    ) {{

        return;
    }}


    const rect =
        viewer.getBoundingClientRect();


    const centerX =
        rect.width / 2;


    const centerY =
        rect.height / 2;


    // Position relative to
    // viewer center.

    const pointX =
        mouseX - centerX;

    const pointY =
        mouseY - centerY;


    const scaleRatio =
        newScale / scale;


    // Keep the point under
    // the cursor fixed.

    translateX =
        pointX -
        (
            pointX -
            translateX
        ) *
        scaleRatio;


    translateY =
        pointY -
        (
            pointY -
            translateY
        ) *
        scaleRatio;


    scale = newScale;


    applyTransform();
}}


// =======================================================
// MOUSE WHEEL
// =======================================================

viewer.addEventListener(
    "wheel",
    function(event) {{

        event.preventDefault();

        event.stopPropagation();


        const rect =
            viewer.getBoundingClientRect();


        const mouseX =
            event.clientX -
            rect.left;


        const mouseY =
            event.clientY -
            rect.top;


        let factor;


        if (
            event.deltaY < 0
        ) {{

            factor = 1.15;

        }} else {{

            factor = 0.87;

        }}


        zoomAt(
            scale * factor,
            mouseX,
            mouseY
        );

    }},
    {{
        passive: false
    }}
);


// =======================================================
// MOUSE DOWN
// =======================================================

viewer.addEventListener(
    "mousedown",
    function(event) {{

        // Only left mouse button.

        if (
            event.button !== 0
        ) {{

            return;
        }}


        // Do not start dragging
        // when clicking buttons.

        if (
            event.target.tagName ===
            "BUTTON"
        ) {{

            return;
        }}


        dragging = true;


        viewer.classList.add(
            "dragging"
        );


        startX =
            event.clientX;


        startY =
            event.clientY;


        startTranslateX =
            translateX;


        startTranslateY =
            translateY;


        event.preventDefault();

    }}
);


// =======================================================
// MOUSE MOVE
// =======================================================

window.addEventListener(
    "mousemove",
    function(event) {{

        if (!dragging) {{

            return;
        }}


        const dx =
            event.clientX -
            startX;


        const dy =
            event.clientY -
            startY;


        translateX =
            startTranslateX +
            dx;


        translateY =
            startTranslateY +
            dy;


        applyTransform();

    }}
);


// =======================================================
// MOUSE UP
// =======================================================

window.addEventListener(
    "mouseup",
    function() {{

        dragging = false;

        viewer.classList.remove(
            "dragging"
        );

    }}
);


// =======================================================
// DOUBLE CLICK RESET
// =======================================================

viewer.addEventListener(
    "dblclick",
    function(event) {{

        if (
            event.target.tagName ===
            "BUTTON"
        ) {{

            return;
        }}


        resetViewer();

    }}
);


// =======================================================
// BUTTON ZOOM IN
// =======================================================

zoomIn.addEventListener(
    "click",
    function(event) {{

        event.stopPropagation();


        const rect =
            viewer.getBoundingClientRect();


        zoomAt(
            scale * 1.25,
            rect.width / 2,
            rect.height / 2
        );

    }}
);


// =======================================================
// BUTTON ZOOM OUT
// =======================================================

zoomOut.addEventListener(
    "click",
    function(event) {{

        event.stopPropagation();


        const rect =
            viewer.getBoundingClientRect();


        zoomAt(
            scale * 0.8,
            rect.width / 2,
            rect.height / 2
        );

    }}
);


// =======================================================
// RESET BUTTON
// =======================================================

resetButton.addEventListener(
    "click",
    function(event) {{

        event.stopPropagation();

        resetViewer();

    }}
);


// =======================================================
// TOUCH SUPPORT
// =======================================================

let touchStartX = 0;

let touchStartY = 0;

let touchStartTranslateX = 0;

let touchStartTranslateY = 0;


viewer.addEventListener(
    "touchstart",
    function(event) {{

        if (
            event.touches.length !== 1
        ) {{

            return;
        }}


        const touch =
            event.touches[0];


        touchStartX =
            touch.clientX;


        touchStartY =
            touch.clientY;


        touchStartTranslateX =
            translateX;


        touchStartTranslateY =
            translateY;

    }},
    {{
        passive: true
    }}
);


viewer.addEventListener(
    "touchmove",
    function(event) {{

        if (
            event.touches.length !== 1
        ) {{

            return;
        }}


        const touch =
            event.touches[0];


        translateX =
            touch.clientX -
            touchStartX +
            touchStartTranslateX;


        translateY =
            touch.clientY -
            touchStartY +
            touchStartTranslateY;


        applyTransform();


        event.preventDefault();

    }},
    {{
        passive: false
    }}
);


// =======================================================
// IMAGE LOAD
// =======================================================

image.addEventListener(
    "load",
    function() {{

        resetViewer();

    }}
);


// =======================================================
// INITIALIZE
// =======================================================

resetViewer();


</script>

</body>

</html>
"""

    st.components.v1.html(
        html,
        height=height,
        scrolling=False,
    )


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


    # =====================================================
    # LOAD ORIGINAL IMAGES
    # =====================================================

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


    # =====================================================
    # AVAILABLE PHOTOS
    # =====================================================

    photo_options = []


    if main_image is not None:

        photo_options.append(
            "Main"
        )


    if closeup_image is not None:

        photo_options.append(
            "Close-up"
        )


    # =====================================================
    # PHOTO SELECTION
    # =====================================================

    if len(photo_options) == 2:

        selected_photo = st.segmented_control(
            "Photo",
            photo_options,
            default="Main",
            width="stretch",
            key=f"detail_photo_{leather_id}",
        )

    elif len(photo_options) == 1:

        selected_photo = (
            photo_options[0]
        )

    else:

        selected_photo = None


    # =====================================================
    # SELECT IMAGE
    # =====================================================

    if selected_photo == "Close-up":

        selected_image = (
            closeup_image
        )

    else:

        selected_image = (
            main_image
        )


    # =====================================================
    # MAIN DETAIL LAYOUT
    # =====================================================

    photo_col, details_col = st.columns(
        [1.55, 1],
        gap="large",
    )


    # =====================================================
    # LEFT SIDE — PHOTO
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

            # ---------------------------------------------
            # INTERACTIVE IMAGE
            # ---------------------------------------------

            interactive_image_viewer(
                selected_image,
                height=VIEWER_HEIGHT,
                key=(
                    f"viewer_"
                    f"{leather_id}_"
                    f"{selected_photo}"
                ),
            )


            st.caption(
                "Scroll mouse wheel to zoom • "
                "Click and drag to move • "
                "Double-click to reset"
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
            str(
                product.get(
                    "leather_id"
                )
                or ""
            ),

            str(
                product.get(
                    "article_name"
                )
                or ""
            ),

            str(
                product.get(
                    "color"
                )
                or ""
            ),

            str(
                product.get(
                    "thickness"
                )
                or ""
            ),

            str(
                product.get(
                    "tannage"
                )
                or ""
            ),

            str(
                product.get(
                    "animal"
                )
                or ""
            ),

            str(
                product.get(
                    "origin"
                )
                or ""
            ),
        ]
    ).lower()


    if (
        search_lower
        and search_lower
        not in searchable_text
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


    filtered_products.append(
        product
    )


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
            f"Showing "
            f"{len(filtered_products)} "
            f"of "
            f"{len(products)} "
            f"leather articles"
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
            x.get("leather_id")
            or ""
        )
    )


elif sort_option == "Article":

    filtered_products.sort(
        key=lambda x: str(
            x.get("article_name")
            or ""
        ).lower()
    )


elif sort_option == "Animal":

    filtered_products.sort(
        key=lambda x: str(
            x.get("animal")
            or ""
        ).lower()
    )


elif sort_option == "Colour":

    filtered_products.sort(
        key=lambda x: str(
            x.get("color")
            or ""
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

        row_products = (
            filtered_products[
                row_start:
                row_start + 4
            ]
        )


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

                    # =====================================
                    # PRODUCT IMAGE
                    # =====================================

                    main_url = get_image_url(
                        product.get(
                            "main_photo"
                        )
                    )


                    main_original = (
                        load_image(
                            main_url
                        )
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


                    # =====================================
                    # ARTICLE NAME
                    # =====================================

                    st.markdown(
                        f"**{product.get('article_name', '-') }**"
                    )


                    # =====================================
                    # LEATHER ID
                    # =====================================

                    st.caption(
                        f"Leather ID: "
                        f"{product.get('leather_id', '-')}"
                    )


                    # =====================================
                    # VIEW DETAILS
                    # =====================================

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
