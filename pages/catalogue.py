import streamlit as st
from supabase import create_client
from urllib.parse import quote
from io import BytesIO
from urllib.request import urlopen
import base64
import html

from PIL import Image, ImageOps


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Leather Catalogue",
    page_icon="🧥",
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

@st.cache_data(
    ttl=300,
    show_spinner=False,
)
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
        .eq(
            "is_active",
            True,
        )
        .order(
            "leather_id"
        )
        .execute()
    )

    return response.data or []


try:

    products = load_products()

except Exception as e:

    st.error(
        "Unable to load the leather catalogue."
    )

    st.exception(e)

    st.stop()


# =========================================================
# IMAGE SETTINGS
# =========================================================

# Catalogue cards
CARD_SIZE = (
    1200,
    675,
)

# Detail viewer
DETAIL_VIEWER_HEIGHT = 500


# =========================================================
# DOWNLOAD IMAGE
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
        quality=92,
        optimize=True,
    )

    return base64.b64encode(
        buffer.getvalue()
    ).decode("utf-8")


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
# AUTO SLIDING CATALOGUE PHOTO
#
# Main photo
#     ↓
# 5 seconds
#     ↓
# Close-up
#     ↓
# 5 seconds
#     ↓
# Main photo
#
# No Streamlit rerun is required.
# =========================================================

def auto_slide_image(
    main_url,
    closeup_url,
    height=220,
    key="",
):

    if not main_url and not closeup_url:

        st.info(
            "Image unavailable"
        )

        return

    # -----------------------------------------------------
    # ONLY MAIN PHOTO
    # -----------------------------------------------------

    if main_url and not closeup_url:

        safe_main_url = html.escape(
            main_url,
            quote=True,
        )

        iframe_html = f"""
        <!DOCTYPE html>

        <html>

        <head>

        <style>

        html,
        body {{
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            overflow: hidden;
            background: white;
        }}

        .photo {{
            width: 100%;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            background: white;
        }}

        img {{
            width: 100%;
            height: 100%;
            object-fit: contain;
            display: block;
        }}

        </style>

        </head>

        <body>

        <div class="photo">

            <img
                src="{safe_main_url}"
                alt="Leather photo"
            >

        </div>

        </body>

        </html>
        """

        st.iframe(
            iframe_html,
            height=height,
        )

        return

    # -----------------------------------------------------
    # MAIN + CLOSE-UP
    # -----------------------------------------------------

    safe_main_url = html.escape(
        main_url,
        quote=True,
    )

    safe_closeup_url = html.escape(
        closeup_url,
        quote=True,
    )

    iframe_html = f"""
    <!DOCTYPE html>

    <html>

    <head>

    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width,
        initial-scale=1.0"
    >

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
        background: white;
    }}

    .slider {{
        position: relative;
        width: 100%;
        height: 100%;
        overflow: hidden;
        background: white;
    }}

    .slide {{
        position: absolute;
        inset: 0;
        width: 100%;
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        opacity: 0;
        transition: opacity 0.8s ease-in-out;
    }}

    .slide.active {{
        opacity: 1;
    }}

    .slide img {{
        width: 100%;
        height: 100%;
        object-fit: contain;
        display: block;
    }}

    .photo-label {{
        position: absolute;
        right: 10px;
        bottom: 10px;
        padding: 4px 8px;
        border-radius: 5px;
        background: rgba(
            0,
            0,
            0,
            0.60
        );
        color: white;
        font-size: 10px;
        z-index: 5;
        opacity: 0;
        transition: opacity 0.4s ease;
    }}

    .slider:hover .photo-label {{
        opacity: 1;
    }}

    </style>

    </head>

    <body>

    <div
        class="slider"
        id="slider"
    >

        <div
            class="slide active"
            id="mainSlide"
        >

            <img
                src="{safe_main_url}"
                alt="Main leather photo"
            >

        </div>

        <div
            class="slide"
            id="closeupSlide"
        >

            <img
                src="{safe_closeup_url}"
                alt="Leather close-up photo"
            >

        </div>

        <div
            class="photo-label"
            id="photoLabel"
        >
            Main
        </div>

    </div>

    <script>

    let showingMain = true;

    const mainSlide =
        document.getElementById(
            "mainSlide"
        );

    const closeupSlide =
        document.getElementById(
            "closeupSlide"
        );

    const photoLabel =
        document.getElementById(
            "photoLabel"
        );

    function switchPhoto() {{

        showingMain = !showingMain;

        if (showingMain) {{

            mainSlide.classList.add(
                "active"
            );

            closeupSlide.classList.remove(
                "active"
            );

            photoLabel.textContent =
                "Main";

        }} else {{

            mainSlide.classList.remove(
                "active"
            );

            closeupSlide.classList.add(
                "active"
            );

            photoLabel.textContent =
                "Close-up";
        }}
    }}

    // ---------------------------------------------------
    // CHANGE EVERY 5 SECONDS
    // ---------------------------------------------------

    setInterval(
        switchPhoto,
        5000
    );

    </script>

    </body>

    </html>
    """

    st.iframe(
        iframe_html,
        height=height,
    )


# =========================================================
# PROFESSIONAL INTERACTIVE DETAIL VIEWER
#
# Initial state:
# Complete photo fitted
#
# Mouse wheel:
# Zoom in / out
#
# Mouse drag:
# Move in every direction
#
# Double click:
# Reset
#
# + / -:
# Zoom
#
# Reset:
# Fit photo back to screen
# =========================================================

def interactive_detail_viewer(
    image,
    height=DETAIL_VIEWER_HEIGHT,
):

    if image is None:

        st.info(
            "No image available."
        )

        return

    image_base64 = image_to_base64(
        image
    )

    if not image_base64:

        st.info(
            "Unable to display image."
        )

        return

    viewer_html = f"""
    <!DOCTYPE html>

    <html>

    <head>

    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width,
        initial-scale=1.0"
    >

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
    }}

    /* ===================================================
       VIEWER
       =================================================== */

    #viewer {{

        position: relative;

        width: 100%;

        height: {height}px;

        overflow: hidden;

        background: #111;

        border-radius: 10px;

        border: 1px solid
            rgba(
                255,
                255,
                255,
                0.14
            );

        cursor: grab;

        user-select: none;

        touch-action: none;
    }}

    #viewer.dragging {{
        cursor: grabbing;
    }}

    /* ===================================================
       IMAGE
       =================================================== */

    #photo {{

        position: absolute;

        left: 50%;

        top: 50%;

        display: block;

        max-width: none;

        max-height: none;

        transform-origin: center center;

        pointer-events: none;

        user-select: none;

        -webkit-user-drag: none;

        will-change: transform;
    }}

    /* ===================================================
       CONTROLS
       =================================================== */

    .controls {{

        position: absolute;

        top: 12px;

        right: 12px;

        z-index: 10;

        display: flex;

        gap: 5px;
    }}

    .control {{

        min-width: 38px;

        height: 38px;

        padding: 0 10px;

        border: none;

        border-radius: 8px;

        background:
            rgba(
                20,
                20,
                20,
                0.85
            );

        color: white;

        font-size: 18px;

        font-weight: 600;

        cursor: pointer;

        backdrop-filter: blur(8px);
    }}

    .control:hover {{

        background:
            rgba(
                55,
                55,
                55,
                0.95
            );
    }}

    .reset {{
        font-size: 12px;
    }}

    /* ===================================================
       ZOOM LABEL
       =================================================== */

    #zoomLabel {{

        position: absolute;

        left: 12px;

        bottom: 12px;

        z-index: 10;

        padding: 5px 9px;

        border-radius: 6px;

        background:
            rgba(
                20,
                20,
                20,
                0.78
            );

        color:
            rgba(
                255,
                255,
                255,
                0.90
            );

        font-size: 11px;
    }}

    /* ===================================================
       HELP
       =================================================== */

    #help {{

        position: absolute;

        left: 50%;

        bottom: 12px;

        transform: translateX(-50%);

        z-index: 10;

        padding: 5px 10px;

        border-radius: 6px;

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
                0.80
            );

        font-size: 11px;

        pointer-events: none;
    }}

    </style>

    </head>

    <body>

    <div id="viewer">

        <!-- =========================================
             CONTROLS
             ========================================= -->

        <div class="controls">

            <button
                id="zoomOut"
                class="control"
                title="Zoom out"
            >
                −
            </button>

            <button
                id="zoomIn"
                class="control"
                title="Zoom in"
            >
                +
            </button>

            <button
                id="reset"
                class="control reset"
                title="Fit photo"
            >
                Fit
            </button>

        </div>


        <!-- =========================================
             PHOTO
             ========================================= -->

        <img
            id="photo"
            src="data:image/jpeg;base64,{image_base64}"
            draggable="false"
            alt="Leather photo"
        >


        <!-- =========================================
             ZOOM LABEL
             ========================================= -->

        <div id="zoomLabel">
            100%
        </div>


        <!-- =========================================
             HELP
             ========================================= -->

        <div id="help">
            Scroll to zoom • Drag to move •
            Double-click to fit
        </div>

    </div>


    <script>

    // =================================================
    // ELEMENTS
    // =================================================

    const viewer =
        document.getElementById(
            "viewer"
        );

    const photo =
        document.getElementById(
            "photo"
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


    // =================================================
    // STATE
    // =================================================

    let baseScale = 1;

    let scale = 1;

    let translateX = 0;

    let translateY = 0;

    let imageWidth = 0;

    let imageHeight = 0;

    let dragging = false;

    let startX = 0;

    let startY = 0;

    let startTranslateX = 0;

    let startTranslateY = 0;

    const MIN_ZOOM = 0.5;

    const MAX_ZOOM = 8;


    // =================================================
    // GET VIEWER SIZE
    // =================================================

    function viewerSize() {{

        return {{

            width:
                viewer.clientWidth,

            height:
                viewer.clientHeight

        }};
    }}


    // =================================================
    // CLAMP PAN
    // =================================================

    function clampPan() {{

        const size =
            viewerSize();

        const renderedWidth =
            imageWidth * scale;

        const renderedHeight =
            imageHeight * scale;

        const maxX =
            Math.max(
                0,
                (
                    renderedWidth
                    - size.width
                ) / 2
            );

        const maxY =
            Math.max(
                0,
                (
                    renderedHeight
                    - size.height
                ) / 2
            );

        translateX =
            Math.max(
                -maxX,
                Math.min(
                    maxX,
                    translateX
                )
            );

        translateY =
            Math.max(
                -maxY,
                Math.min(
                    maxY,
                    translateY
                )
            );
    }}


    // =================================================
    // UPDATE LABEL
    // =================================================

    function updateLabel() {{

        const relativeZoom =
            scale / baseScale;

        zoomLabel.textContent =
            Math.round(
                relativeZoom * 100
            ) + "%";
    }}


    // =================================================
    // APPLY TRANSFORM
    // =================================================

    function applyTransform() {{

        clampPan();

        photo.style.transform =
            "translate(-50%, -50%) "
            +
            "translate("
            + translateX
            + "px, "
            + translateY
            + "px) "
            +
            "scale("
            + scale
            + ")";

        updateLabel();
    }}


    // =================================================
    // FIT PHOTO
    // =================================================

    function fitPhoto() {{

        const size =
            viewerSize();

        if (
            imageWidth <= 0
            ||
            imageHeight <= 0
        ) {{

            return;
        }}

        const widthScale =
            (
                size.width - 20
            )
            /
            imageWidth;

        const heightScale =
            (
                size.height - 20
            )
            /
            imageHeight;

        baseScale =
            Math.min(
                widthScale,
                heightScale
            );

        baseScale =
            Math.max(
                0.01,
                baseScale
            );

        scale = baseScale;

        translateX = 0;

        translateY = 0;

        applyTransform();
    }}


    // =================================================
    // ZOOM AROUND CURSOR
    // =================================================

    function zoomAt(
        requestedScale,
        mouseX,
        mouseY
    ) {{

        const oldScale =
            scale;

        const newScale =
            Math.max(
                baseScale * MIN_ZOOM,
                Math.min(
                    baseScale * MAX_ZOOM,
                    requestedScale
                )
            );

        if (
            Math.abs(
                newScale - oldScale
            ) < 0.0001
        ) {{

            return;
        }}

        const size =
            viewerSize();

        const centerX =
            size.width / 2;

        const centerY =
            size.height / 2;

        const pointX =
            mouseX - centerX;

        const pointY =
            mouseY - centerY;

        const ratio =
            newScale / oldScale;

        translateX =
            pointX
            -
            (
                pointX
                -
                translateX
            )
            *
            ratio;

        translateY =
            pointY
            -
            (
                pointY
                -
                translateY
            )
            *
            ratio;

        scale =
            newScale;

        applyTransform();
    }}


    // =================================================
    // MOUSE WHEEL
    // =================================================

    viewer.addEventListener(
        "wheel",
        function(event) {{

            event.preventDefault();

            event.stopPropagation();

            const rect =
                viewer.getBoundingClientRect();

            const mouseX =
                event.clientX
                -
                rect.left;

            const mouseY =
                event.clientY
                -
                rect.top;

            if (
                event.deltaY < 0
            ) {{

                zoomAt(
                    scale * 1.15,
                    mouseX,
                    mouseY
                );

            }} else {{

                zoomAt(
                    scale * 0.87,
                    mouseX,
                    mouseY
                );
            }

        },
        {
            passive: false
        }
    );


    // =================================================
    // MOUSE DOWN
    // =================================================

    viewer.addEventListener(
        "mousedown",
        function(event) {{

            if (
                event.button !== 0
            ) {{

                return;
            }}

            if (
                event.target.tagName
                ===
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

        }
    );


    // =================================================
    // MOUSE MOVE
    // =================================================

    window.addEventListener(
        "mousemove",
        function(event) {{

            if (!dragging) {{
                return;
            }}

            translateX =
                startTranslateX
                +
                (
                    event.clientX
                    -
                    startX
                );

            translateY =
                startTranslateY
                +
                (
                    event.clientY
                    -
                    startY
                );

            applyTransform();

        }
    );


    // =================================================
    // MOUSE UP
    // =================================================

    window.addEventListener(
        "mouseup",
        function() {{

            dragging = false;

            viewer.classList.remove(
                "dragging"
            );

        }
    );


    // =================================================
    // DOUBLE CLICK
    // =================================================

    viewer.addEventListener(
        "dblclick",
        function(event) {{

            if (
                event.target.tagName
                ===
                "BUTTON"
            ) {{

                return;
            }}

            fitPhoto();

        }
    );


    // =================================================
    // ZOOM IN
    // =================================================

    zoomIn.addEventListener(
        "click",
        function(event) {{

            event.stopPropagation();

            const size =
                viewerSize();

            zoomAt(
                scale * 1.25,
                size.width / 2,
                size.height / 2
            );

        }
    );


    // =================================================
    // ZOOM OUT
    // =================================================

    zoomOut.addEventListener(
        "click",
        function(event) {{

            event.stopPropagation();

            const size =
                viewerSize();

            zoomAt(
                scale * 0.8,
                size.width / 2,
                size.height / 2
            );

        }
    );


    // =================================================
    // FIT BUTTON
    // =================================================

    resetButton.addEventListener(
        "click",
        function(event) {{

            event.stopPropagation();

            fitPhoto();

        }
    );


    // =================================================
    // TOUCH DRAG
    // =================================================

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

        },
        {
            passive: true
        }
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
                touch.clientX
                -
                touchStartX
                +
                touchStartTranslateX;

            translateY =
                touch.clientY
                -
                touchStartY
                +
                touchStartTranslateY;

            applyTransform();

            event.preventDefault();

        },
        {
            passive: false
        }
    );


    // =================================================
    // IMAGE LOADED
    // =================================================

    photo.addEventListener(
        "load",
        function() {{

            imageWidth =
                photo.naturalWidth;

            imageHeight =
                photo.naturalHeight;

            photo.style.width =
                imageWidth + "px";

            photo.style.height =
                imageHeight + "px";

            fitPhoto();

        }
    );


    // =================================================
    // WINDOW RESIZE
    // =================================================

    window.addEventListener(
        "resize",
        function() {{

            fitPhoto();

        }
    );

    </script>

    </body>

    </html>
    """

    st.iframe(
        viewer_html,
        height=height,
    )


# =========================================================
# DETAIL INFORMATION
# =========================================================

def show_detail_information(
    product,
    main_image,
    closeup_image,
):

    leather_id = str(
        product.get(
            "leather_id"
        )
        or "-"
    )

    article_name = str(
        product.get(
            "article_name"
        )
        or "-"
    )

    color = str(
        product.get(
            "color"
        )
        or "-"
    )

    thickness = str(
        product.get(
            "thickness"
        )
        or "-"
    )

    animal = str(
        product.get(
            "animal"
        )
        or "-"
    )

    tannage = str(
        product.get(
            "tannage"
        )
        or "-"
    )

    origin = str(
        product.get(
            "origin"
        )
        or "-"
    )

    st.markdown(
        "### Product Information"
    )

    # =====================================================
    # ROW 1
    # =====================================================

    col1, col2 = st.columns(
        2,
        gap="medium",
    )

    with col1:

        st.caption(
            "Leather ID"
        )

        st.write(
            leather_id
        )

    with col2:

        st.caption(
            "Article Name"
        )

        st.write(
            article_name
        )

    # =====================================================
    # ROW 2
    # =====================================================

    col1, col2 = st.columns(
        2,
        gap="medium",
    )

    with col1:

        st.caption(
            "Colour"
        )

        st.write(
            color
        )

    with col2:

        st.caption(
            "Thickness"
        )

        st.write(
            thickness
        )

    # =====================================================
    # ROW 3
    # =====================================================

    col1, col2 = st.columns(
        2,
        gap="medium",
    )

    with col1:

        st.caption(
            "Animal"
        )

        st.write(
            animal
        )

    with col2:

        st.caption(
            "Tannage"
        )

        st.write(
            tannage
        )

    # =====================================================
    # ROW 4
    # =====================================================

    col1, col2 = st.columns(
        2,
        gap="medium",
    )

    with col1:

        st.caption(
            "Origin"
        )

        st.write(
            origin
        )

    with col2:

        st.caption(
            "Photos"
        )

        if (
            main_image is not None
            and
            closeup_image is not None
        ):

            st.write(
                "Main + Close-up"
            )

        elif main_image is not None:

            st.write(
                "Main only"
            )

        elif closeup_image is not None:

            st.write(
                "Close-up only"
            )

        else:

            st.write(
                "No photos"
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
        product.get(
            "leather_id"
        )
        or "-"
    )

    article_name = str(
        product.get(
            "article_name"
        )
        or "-"
    )

    main_url = get_image_url(
        product.get(
            "main_photo"
        )
    )

    closeup_url = get_image_url(
        product.get(
            "closeup_photo"
        )
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
    # PHOTO OPTIONS
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
    # PHOTO SELECTOR
    # =====================================================

    if len(photo_options) == 2:

        selected_photo = st.segmented_control(
            "Photo",
            photo_options,
            default="Main",
            width="stretch",
            key=(
                f"detail_photo_"
                f"{leather_id}"
            ),
        )

    elif len(photo_options) == 1:

        selected_photo = photo_options[0]

    else:

        selected_photo = None

    # =====================================================
    # SELECT CURRENT IMAGE
    # =====================================================

    if selected_photo == "Close-up":

        selected_image = closeup_image

    else:

        selected_image = main_image

    # =====================================================
    # MAIN DIALOG LAYOUT
    #
    # Photo = left
    # Information = right
    # =====================================================

    photo_col, details_col = st.columns(
        [1.65, 1],
        gap="large",
    )

    # =====================================================
    # PHOTO
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

            interactive_detail_viewer(
                selected_image,
                height=DETAIL_VIEWER_HEIGHT,
            )

        st.caption(
            "Scroll to zoom • "
            "Drag to move • "
            "Double-click or Fit to reset"
        )

    # =====================================================
    # INFORMATION
    # =====================================================

    with details_col:

        show_detail_information(
            product,
            main_image,
            closeup_image,
        )


# =========================================================
# HEADER
# =========================================================

st.title(
    "Leather Catalogue"
)

st.caption(
    "Explore our leather collection by article, "
    "colour, animal, tannage and origin."
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
            "Search leather ID, article, colour, "
            "animal, tannage or origin..."
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
        str(
            p["animal"]
        ).strip()
        for p in products
        if p.get("animal")
    }
)

tannages = sorted(
    {
        str(
            p["tannage"]
        ).strip()
        for p in products
        if p.get("tannage")
    }
)

colors = sorted(
    {
        str(
            p["color"]
        ).strip()
        for p in products
        if p.get("color")
    }
)

origins = sorted(
    {
        str(
            p["origin"]
        ).strip()
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

    with st.container(
        border=True
    ):

        st.subheader(
            "Filter"
        )

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
            f"{len(products)} "
            f"total leather articles"
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

    # -----------------------------------------------------
    # SEARCH
    # -----------------------------------------------------

    if (
        search_lower
        and
        search_lower not in searchable_text
    ):

        continue

    # -----------------------------------------------------
    # ANIMAL
    # -----------------------------------------------------

    if selected_animals:

        if (
            product.get(
                "animal"
            )
            not in selected_animals
        ):

            continue

    # -----------------------------------------------------
    # TANNAGE
    # -----------------------------------------------------

    if selected_tannages:

        if (
            product.get(
                "tannage"
            )
            not in selected_tannages
        ):

            continue

    # -----------------------------------------------------
    # COLOUR
    # -----------------------------------------------------

    if selected_colors:

        if (
            product.get(
                "color"
            )
            not in selected_colors
        ):

            continue

    # -----------------------------------------------------
    # ORIGIN
    # -----------------------------------------------------

    if selected_origins:

        if (
            product.get(
                "origin"
            )
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
            x.get(
                "leather_id"
            )
            or ""
        )
    )

elif sort_option == "Article":

    filtered_products.sort(
        key=lambda x: str(
            x.get(
                "article_name"
            )
            or ""
        ).lower()
    )

elif sort_option == "Animal":

    filtered_products.sort(
        key=lambda x: str(
            x.get(
                "animal"
            )
            or ""
        ).lower()
    )

elif sort_option == "Colour":

    filtered_products.sort(
        key=lambda x: str(
            x.get(
                "color"
            )
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

        row_products = filtered_products[
            row_start:
            row_start + 4
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

                    # =====================================
                    # IMAGE URLs
                    # =====================================

                    main_url = get_image_url(
                        product.get(
                            "main_photo"
                        )
                    )

                    closeup_url = get_image_url(
                        product.get(
                            "closeup_photo"
                        )
                    )

                    # =====================================
                    # AUTO-SLIDING IMAGE
                    #
                    # MAIN
                    # ↓ 5 sec
                    # CLOSE-UP
                    # ↓ 5 sec
                    # MAIN
                    # =====================================

                    if (
                        main_url
                        or
                        closeup_url
                    ):

                        auto_slide_image(
                            main_url,
                            closeup_url,
                            height=220,
                            key=str(
                                product.get(
                                    "leather_id"
                                )
                            ),
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
                        "Leather ID: "
                        f"{product.get('leather_id', '-')}"
                    )

                    # =====================================
                    # DETAILS BUTTON
                    # =====================================

                    if st.button(
                        "View details",
                        key=(
                            "details_"
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
